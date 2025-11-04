import logging

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.accounts.exceptions import InvalidUserIdError
from apps.events.services.permission_service import EventPermissionService
from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.storage.optimized_s3_service import OptimizedS3Service
from apps.shared.utils.general import get_user_by_id

from ..dal import AlbumDAL
from ..models import Album

logger = logging.getLogger(__name__)


class AlbumService:
    """
    Сервісний шар для роботи з альбомами.
    Забезпечує бізнес-логіку для CRUD операцій з альбомами та інтеграцію з S3.
    """

    def __init__(self, s3service=None, dal=None, permission_service=None):
        """
        Ініціалізація сервісу з опціональними залежностями.

        Args:
            s3service: S3 сервіс для роботи з файлами
            dal: Data Access Layer для альбомів
            permission_service: Сервіс для перевірки дозволів
        """
        self.s3service = s3service or OptimizedS3Service()
        self.dal = dal or AlbumDAL()
        # Використовуємо lazy import для уникнення циклічних залежностей
        self._permission_service = permission_service

    @property
    def permission_service(self):
        """Lazy initialization EventPermissionService"""
        if self._permission_service is None:
            self._permission_service = EventPermissionService()
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

        # Перевіряємо чи користувач є власником події
        if event.user_id != user_id:
            logger.warning(f'User {user_id} attempted to create album for event {event.id} without ownership')
            raise PermissionDenied('Only event owner can create albums.')

        # Спочатку створюємо альбом БЕЗ збереження в БД
        album = Album(
            event=event,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_public=serializer.validated_data.get('is_public', False),
        )

        # Генеруємо S3 prefix до збереження
        album_folder_name = f'user-bucket-{user.pk}/{event.event_uuid}/album-{album.album_uuid}'
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
        # Використовуємо EventPermissionService для перевірки доступу
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
