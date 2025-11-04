import logging
import mimetypes
import uuid

from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied

from apps.albums.models import Album
from apps.events.models import Event
from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.exceptions.exception import S3UploadException
from apps.shared.storage.optimized_s3_service import OptimizedS3Service
from apps.shared.storage.s3_utils import file_generate_name

from ..models import MediaFile

logger = logging.getLogger(__name__)


class MediafileService:
    """
    Сервісний шар для роботи з медіафайлами.
    Забезпечує бізнес-логіку для операцій з файлами та інтеграцію з S3.
    """

    def __init__(self, s3service=None, permission_service=None):
        """
        Ініціалізація сервісу з опціональними залежностями.

        Args:
            s3service: S3 сервіс для роботи з файлами
            permission_service: Сервіс для перевірки дозволів
        """
        self.s3service = s3service or OptimizedS3Service()
        # Використовуємо lazy import для уникнення циклічних залежностей
        self._permission_service = permission_service

    @property
    def permission_service(self):
        """Lazy initialization EventPermissionService"""
        if self._permission_service is None:
            from apps.events.services.permission_service import EventPermissionService

            self._permission_service = EventPermissionService()
        return self._permission_service

    def create_mediafile(self, serializer, user, album_pk):
        """
        Створення медіафайлу з завантаженням в S3.

        Args:
            serializer: Валідований серіалізатор з даними файлу
            user: Об'єкт користувача
            album_pk: ID альбому

        Returns:
            MediaFile: Створений медіафайл

        Raises:
            ValidationError: Якщо дані невалідні або альбом не знайдено
            S3UploadException: При помилці завантаження в S3
        """
        validated_data = serializer.validated_data
        file = validated_data.get('file')

        if not file:
            logger.error('File creation attempted without file')
            raise ValidationError('File field is required')

        album = self._get_album(album_pk)
        validated_data = self._prepare_validated_data(validated_data, file, user, album)

        # Завантажуємо файл в S3
        self._upload_file_to_s3(file, validated_data, album)

        # Зберігаємо в БД
        mediafile = serializer.save()
        logger.info(f'MediaFile {mediafile.id} created successfully for album {album_pk}')

        return mediafile

    def generate_upload_url_by_uuid(self, event_uuid, user_id, album_name, file_type):
        """
        Генерація presigned URL для завантаження файлу за UUID події.

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            album_name: UUID альбому
            file_type: MIME тип файлу

        Returns:
            dict: Словник з URL для завантаження та ключем storage

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має прав на завантаження
            ValidationError: Якщо формат файлу не підтримується
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Валідація формату файлу
        self._validate_file_type(file_type)

        file_uuid = str(uuid.uuid4())

        # Генеруємо ключ для S3
        storage_key = f'user-bucket-{user_id}/{event.event_gallery_url}/{album_name}/{file_uuid}'

        try:
            presigned_url = self.s3service.generate_upload_url(key=storage_key, content_type=file_type, expiration=3600)

            logger.info(f'Generated upload URL for event {event_uuid}, album {album_name}, user {user_id}')
            return {
                'upload_url': presigned_url,
                'storage_key': storage_key,
                'file_uuid': file_uuid,
                'expires_in': 3600,
                'storage_provider': 's3',
            }
        except Exception as e:
            logger.error(f'Failed to generate presigned URL: {e!s}')
            raise S3ServiceError(f'Failed to generate upload URL: {e!s}')

    def generate_download_url_by_uuid(self, event_uuid, user_id, s3_key, filename=None):
        """
        Генерація presigned URL для завантаження файлу за UUID події.

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            s3_key: Ключ файлу в S3
            filename: Кастомне ім'я файлу для завантаження

        Returns:
            dict: Словник з URL для завантаження

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має прав на доступ
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Перевіряємо чи файл належить до цієї події
        if not self._validate_file_access(s3_key, user_id, event):
            raise PermissionDenied('Access denied to this file')

        try:
            presigned_url = self.s3service.generate_download_url(key=s3_key, expiration=3600, filename=filename)

            logger.info(f'Generated download URL for file {s3_key}, user {user_id}')
            return {'download_url': presigned_url, 's3_key': s3_key, 'expires_in': 3600}
        except Exception as e:
            logger.error(f'Failed to generate download URL: {e!s}')
            raise S3ServiceError(f'Failed to generate download URL: {e!s}')

    def generate_bulk_download_urls_by_uuid(self, event_uuid, user_id, s3_keys):
        """
        Генерація presigned URLs для завантаження множини файлів за UUID події.

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            s3_keys: Список ключів файлів в S3

        Returns:
            dict: Словник з URLs для завантаження

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має прав на доступ
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Фільтруємо тільки файли, що належать до цієї події
        event_prefix = f'user-bucket-{user_id}/{event.event_gallery_url}/'
        authorized_keys = [key for key in s3_keys if key.startswith(event_prefix)]

        if not authorized_keys:
            raise PermissionDenied('No authorized files found')

        try:
            urls = self.s3service.generate_bulk_download_urls(keys=authorized_keys, expiration=3600)

            logger.info(f'Generated bulk download URLs for {len(authorized_keys)} files, user {user_id}')
            return {'download_urls': urls, 'total_files': len(authorized_keys), 'expires_in': 3600}
        except Exception as e:
            logger.error(f'Failed to generate bulk download URLs: {e!s}')
            raise S3ServiceError(f'Failed to generate bulk download URLs: {e!s}')

    def delete_file_by_uuid(self, event_uuid, user_id, s3_key):
        """
        Видалення файлу з S3 за UUID події.

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            s3_key: Ключ файлу в S3

        Returns:
            bool: True якщо видалення успішне

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має прав на видалення
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Перевіряємо чи файл належить до цієї події
        if not self._validate_file_access(s3_key, user_id, event):
            raise PermissionDenied('Access denied to this file')

        try:
            self.s3service.delete_s3_object(s3_key)
            logger.info(f'Deleted file {s3_key}, user {user_id}')
            return True
        except Exception as e:
            logger.error(f'Failed to delete file {s3_key}: {e!s}')
            raise S3ServiceError(f'Failed to delete file: {e!s}')

    def get_file_metadata_by_uuid(self, event_uuid, user_id, s3_key):
        """
        Отримання метаданих файлу за UUID події.

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            s3_key: Ключ файлу в S3

        Returns:
            dict: Метадані файлу

        Raises:
            NotFound: Якщо подію або файл не знайдено
            PermissionDenied: Якщо користувач не має прав на доступ
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Перевіряємо чи файл належить до цієї події
        if not self._validate_file_access(s3_key, user_id, event):
            raise PermissionDenied('Access denied to this file')

        try:
            metadata = self.s3service.get_object_metadata(s3_key)
            logger.info(f'Retrieved metadata for file {s3_key}, event {event_uuid}, user {user_id}')
            return metadata
        except Exception as e:
            logger.error(f'Failed to get file metadata {s3_key}: {e!s}')
            raise S3ServiceError(f'Failed to get file metadata: {e!s}')

    def process_uploaded_file_by_uuid(self, event_uuid, user_id, s3_key, file_type, file_uuid=None):
        """
        Обробка завантаженого файлу за UUID події (створення thumbnail тощо).

        Args:
            event_uuid: UUID події
            user_id: ID користувача
            s3_key: Ключ файлу в S3
            file_type: MIME тип файлу
            file_uuid: UUID файлу (опціонально)

        Returns:
            dict: Результат обробки файлу

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має прав на доступ
        """
        # Отримуємо подію та перевіряємо доступ
        event = self._get_event_by_uuid_with_access_check(event_uuid, user_id)

        # Перевіряємо чи файл належить до цієї події
        if not self._validate_file_access(s3_key, user_id, event):
            raise PermissionDenied('Access denied to this file')

        try:
            # Обробка файлу (thumbnails, metadata extraction тощо)
            result = self.s3service.process_uploaded_file(s3_key, file_type)

            # Можна додати збереження в базу даних
            # self._save_file_record(event.id, user_id, s3_key, file_type, result)

            logger.info(f'Processed uploaded file {s3_key}, user {user_id}')
            return result
        except Exception as e:
            logger.error(f'Failed to process file {s3_key}: {e!s}')
            raise S3ServiceError(f'Failed to process file: {e!s}')

    def get_files_for_album(self, album_id, user_id):
        """
        Отримання списку файлів для альбому з перевіркою доступу.

        Args:
            album_id: ID альбому
            user_id: ID користувача

        Returns:
            QuerySet: Список медіафайлів альбому

        Raises:
            PermissionDenied: Якщо користувач не має доступу до альбому
        """
        album = self._get_album(album_id)

        # Перевіряємо доступ до події альбому
        # Перевіряємо доступ до події через permission service
        try:
            self.permission_service.validate_guest_or_owner_access(album.event, user_id)
        except:
            logger.warning(f'User {user_id} attempted to access files for album {album_id} without permission')
            raise PermissionDenied('You do not have permission to view files in this album.')

        return MediaFile.objects.filter(album_id=album_id).order_by('-created_at')

    # ==============================================================================
    # HELPER METHODS
    # ==============================================================================

    def _get_album(self, album_pk):
        """
        Отримання альбому за ID з обробкою помилок.

        Args:
            album_pk: ID альбому

        Returns:
            Album: Об'єкт альбому

        Raises:
            ValidationError: Якщо альбом не знайдено
        """
        try:
            return Album.objects.get(pk=album_pk)
        except Album.DoesNotExist:
            logger.error(f'Album {album_pk} not found')
            raise ValidationError('Album not found')

    def _prepare_validated_data(self, validated_data, file, user, album):
        """
        Підготовка валідованих даних для збереження файлу.

        Args:
            validated_data: Валідовані дані з серіалізатора
            file: Об'єкт файлу
            user: Об'єкт користувача
            album: Об'єкт альбому

        Returns:
            dict: Підготовлені дані
        """
        validated_data['S3_object_key'] = file_generate_name(file.name)
        validated_data['S3_bucket_name'] = str(user.pk)
        mime_type, _ = mimetypes.guess_type(file.name)
        validated_data['file_type'] = mime_type or ''
        validated_data['user_pk'] = user.pk
        validated_data['album_pk'] = album.pk
        return validated_data

    def _upload_file_to_s3(self, file, validated_data, album):
        """
        Завантаження файлу в S3.

        Args:
            file: Об'єкт файлу
            validated_data: Підготовлені дані
            album: Об'єкт альбому

        Raises:
            S3UploadException: При помилці завантаження
        """
        try:
            s3_key = f"{album.album_s3_prefix}/{validated_data['S3_object_key']}"
            logger.info(f'Uploading file to S3: {s3_key}')

            self.s3service.upload_file(file, validated_data['S3_bucket_name'], s3_key)

            logger.info(f'File uploaded successfully to: {s3_key}')
        except Exception as e:
            logger.error(f'Failed to upload file to S3: {e!s}')
            raise S3UploadException(str(e))

    def _get_event_by_uuid_with_access_check(self, event_uuid, user_id):
        """
        Отримати подію за UUID з перевіркою доступу.

        Args:
            event_uuid: UUID події
            user_id: ID користувача

        Returns:
            Event: Об'єкт події

        Raises:
            NotFound: Якщо подію не знайдено
            PermissionDenied: Якщо користувач не має доступу
        """
        try:
            event = Event.objects.get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            logger.error(f'Event {event_uuid} not found')
            raise NotFound('Подію не знайдено')

        # Перевіряємо доступ до події через permission service
        try:
            self.permission_service.validate_guest_or_owner_access(event, user_id)
        except:
            logger.warning(f'User {user_id} attempted to access event {event_uuid} without permission')
            raise PermissionDenied('Ви не маєте доступу до цієї події')

        return event

    def _validate_file_access(self, s3_key, user_id, event):
        """
        Валідація доступу до файлу.

        Args:
            s3_key: Ключ файлу в S3
            user_id: ID користувача
            event: Об'єкт події

        Returns:
            bool: True якщо доступ дозволено
        """
        return s3_key.startswith(f'user-bucket-{user_id}/{event.event_gallery_url}/')

    def _validate_file_type(self, file_type):
        """
        Валідація типу файлу.

        Args:
            file_type: MIME тип файлу

        Raises:
            ValidationError: Якщо тип файлу не підтримується
        """
        allowed_types = [
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/gif',
            'image/webp',
            'video/mp4',
            'video/mov',
            'video/avi',
            'video/quicktime',
            'application/pdf',
        ]

        if file_type not in allowed_types:
            logger.warning(f'Unsupported file type attempted: {file_type}')
            raise ValidationError(
                f"Непідтримуваний тип файлу: {file_type}. " f"Дозволені типи: {', '.join(allowed_types)}"
            )
