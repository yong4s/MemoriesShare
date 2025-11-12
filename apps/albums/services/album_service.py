import logging

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.accounts.exceptions import InvalidUserIdError
from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.interfaces.permission_interface import IPermissionValidator
from apps.shared.interfaces.service_interfaces import IAlbumService, IS3Service
from apps.shared.services.permission_factory import get_permission_validator
from apps.shared.utils.general import get_user_by_id

from ..dal import AlbumDAL
from ..models import Album

logger = logging.getLogger(__name__)


class AlbumService(IAlbumService):
    """
    Сервісний шар для роботи з альбомами.
    Забезпечує бізнес-логіку для CRUD операцій з альбомами та інтеграцію з S3.
    """

    def __init__(self, s3service: IS3Service = None, dal=None, permission_service=None):
        """
        Ініціалізація сервісу з опціональними залежностями.

        Args:
            s3service: S3 сервіс для роботи з файлами (реалізація IS3Service)
            dal: Data Access Layer для альбомів
            permission_service: IPermissionValidator для перевірки дозволів
        """
        # S3Service буде ін'єктований через service factory
        self._s3service = s3service
        self.dal = dal or AlbumDAL()
        # Використовуємо інтерфейс для розірвання циклічних залежностей
        self._permission_service = permission_service

    @property
    def s3service(self) -> IS3Service:
        """Lazy initialization of S3 service using factory pattern"""
        if self._s3service is None:
            from apps.shared.services.service_factory import get_service, ServiceNames
            self._s3service = get_service(ServiceNames.S3_SERVICE)
        return self._s3service

    @property
    def permission_service(self) -> IPermissionValidator:
        """Lazy initialization of permission validator using factory pattern"""
        if self._permission_service is None:
            # Використовуємо фабрику для створення підходящого валідатора
            self._permission_service = get_permission_validator(context="album")
        return self._permission_service

    def create_album(self, serializer, event, user_id):
        """
        Створення альбому для події з валідацією прав та S3 інтеграцією.

        Args:
            serializer: AlbumCreateSerializer з валідними даними
            event: Event об'єкт
            user_id: ID користувача

        Returns:
            Album: Створений альбом

        Raises:
            PermissionDenied: Якщо користувач не має прав
            S3ServiceError: При помилці створення S3 структури
            InvalidUserIdError: Якщо користувача не знайдено
        """
        if not user_id or not event:
            logger.warning(f'Album creation attempt with invalid parameters: user_id={user_id}, event={event}')
            raise PermissionDenied('You do not have permission to add albums to this event.')

        try:
            user = get_user_by_id(user_id)
        except InvalidUserIdError:
            logger.error(f'Invalid user ID provided for album creation: {user_id}')
            raise

        # Перевіряємо чи користувач є власником події через permission service
        try:
            self.permission_service.validate_owner_access(event, user_id)
        except PermissionDenied:
            logger.warning(f'User {user_id} attempted to create album for event {event.id} without ownership')
            raise PermissionDenied('Only event owner can create albums.')

        # Спочатку створюємо альбом БЕЗ збереження в БД
        album = Album(
            event=event,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_public=serializer.validated_data.get('is_public', False),
        )

        # Генеруємо S3 prefix до збереження: users/{user_uuid}/events/{event_uuid}/albums/{album_uuid}
        album_folder_name = f'users/{user.user_uuid}/events/{event.event_uuid}/albums/{album.album_uuid}'
        album.album_s3_prefix = album_folder_name

        try:
            logger.info(f'Creating S3 folder: {album_folder_name}')
            result = self.s3service.create_folder(album_folder_name)
            logger.info(f'S3 folder creation result: {result}')

            # Перевіряємо чи результат містить помилку
            if 'Error' in str(result):
                raise Exception(f'S3 folder creation failed: {result}')

            # Тільки ПІСЛЯ успішного створення S3 папки зберігаємо в БД
            album.save()
            logger.info(f'Album {album.album_uuid} created successfully with S3 prefix: {album_folder_name}')

        except Exception as e:
            # S3 папка не створилася - не зберігаємо в БД взагалі
            logger.error(f'Failed to create S3 folder for album: {e!s}')
            raise S3ServiceError(f'Failed to create album folder: {e!s}')

        return album

    def get_album(self, user_id, album_id):
        album = self.dal.get_album_by_id(album_id)

        if not self._is_owner_or_guest(album.event_id, user_id):
            logger.warning(f'User {user_id} attempted to access album {album_id} without permission')
            raise PermissionDenied('You do not have permission to view this album.')

        return album

    def get_albums_for_event(self, user_id, event_id):
        if not self._is_owner_or_guest(event_id, user_id):
            logger.warning(f'User {user_id} attempted to access albums for event {event_id} without permission')
            raise PermissionDenied('You do not have permission to view albums for this event.')

        return self.dal.get_all_event_albums(event_id)

    def update_album(self, user_id, album_id, album_data):
        """
        Оновлення альбому з перевіркою прав власника.

        Args:
            user_id: ID користувача
            album_id: ID альбому
            album_data: Дані для оновлення

        Returns:
            Album: Оновлений альбом

        Raises:
            PermissionDenied: Якщо користувач не є власником події
        """
        album = self.dal.get_album_by_id(album_id)

        # Перевіряємо чи користувач є власником події через сервіс
        try:
            self.permission_service.validate_owner_access(album.event, user_id)
        except:
            logger.warning(f'User {user_id} attempted to update album {album_id} without ownership')
            raise PermissionDenied('Only event owner can update albums.')

        # Оновлюємо поля альбому
        for field, value in album_data.items():
            if hasattr(album, field):
                setattr(album, field, value)

        album.save()
        logger.info(f'Album {album_id} updated successfully by user {user_id}')

        return album

    def delete_album(self, user_id, album_id):
        """
        Видалення альбому з S3 структурою та перевіркою прав.

        Args:
            user_id: ID користувача
            album_id: ID альбому

        Returns:
            bool: True якщо видалення успішне

        Raises:
            PermissionDenied: Якщо користувач не є власником події
            S3ServiceError: При помилці видалення S3 структури
        """
        album = self.dal.get_album_by_id(album_id)

        # Перевіряємо чи користувач є власником події через сервіс
        try:
            self.permission_service.validate_owner_access(album.event, user_id)
        except:
            logger.warning(f'User {user_id} attempted to delete album {album_id} without ownership')
            raise PermissionDenied('You do not have permission to delete albums for this event.')

        album_folder_url = album.album_s3_prefix

        try:
            # Спочатку видаляємо S3 структуру
            if album_folder_url:
                logger.info(f'Deleting S3 folder: {album_folder_url}')
                self.s3service.delete_folder(album_folder_url)
                logger.info(f'S3 folder deleted successfully: {album_folder_url}')
        except Exception as e:
            logger.error(f'Failed to delete S3 folder for album {album_id}: {e!s}')
            raise S3ServiceError(f'Failed to delete album folder: {e!s}')

        # Потім видаляємо з БД
        result = self.dal.delete_album(album_id)
        logger.info(f'Album {album_id} deleted successfully by user {user_id}')

        return result

    def _is_owner_or_guest(self, event_id, user_id):
        """
        Перевірка чи є користувач власником події або її гостем.

        Args:
            event_id: ID події
            user_id: ID користувача

        Returns:
            bool: True якщо користувач має доступ
        """
        # Використовуємо permission service через інтерфейс для перевірки доступу
        try:
            from apps.events.models import Event

            event = Event.objects.get(id=event_id)
            self.permission_service.validate_guest_or_owner_access(event, user_id)
            return True
        except:
            return False

    def get_album_statistics(self, album_id, user_id):
        """
        Отримання статистики альбому (кількість файлів, розмір тощо).

        Args:
            album_id: ID альбому
            user_id: ID користувача

        Returns:
            dict: Статистика альбому

        Raises:
            PermissionDenied: Якщо користувач не має прав на перегляд
        """
        album = self.get_album(user_id, album_id)

        # Отримуємо статистику через DAL
        stats = self.dal.get_album_statistics(album_id)

        return {
            'album_id': album_id,
            'album_name': album.name,
            'total_files': stats.get('file_count', 0),
            'total_size_bytes': stats.get('total_size', 0),
            'created_at': album.created_at,
            'last_modified': album.updated_at,
            'is_public': album.is_public,
        }
