"""
Валідатори для безпечної роботи з файлами та S3 ключами.
"""

import re
import uuid

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class S3KeyValidator:
    """Валідатор для S3 ключів та безпечних шляхів"""

    # Дозволені символи в назвах файлів та папок
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_\.]+$')
    UUID_PATTERN = re.compile(r'^[a-f0-9\-]{36}$')
    ALBUM_UUID_PATTERN = re.compile(r'^[a-f0-9\-]{36}$')

    # Максимальні довжини
    MAX_FILENAME_LENGTH = 255
    MAX_PATH_DEPTH = 10

    @classmethod
    def validate_album_name(cls, album_name: str) -> str:
        """
        Валідація назви альбому (має бути UUID).

        Args:
            album_name: Назва альбому для валідації

        Returns:
            str: Валідована назва альбому

        Raises:
            ValidationError: Якщо назва альбому невалідна
        """
        if not album_name:
            raise ValidationError(_('Назва альбому не може бути порожньою'))

        if not cls.ALBUM_UUID_PATTERN.match(album_name):
            raise ValidationError(_('Назва альбому має бути валідним UUID'))

        try:
            uuid.UUID(album_name)
        except ValueError:
            raise ValidationError(_('Назва альбому має бути валідним UUID'))

        return album_name

    @classmethod
    def validate_file_uuid(cls, file_uuid: str) -> str:
        """
        Валідація UUID файлу.

        Args:
            file_uuid: UUID файлу для валідації

        Returns:
            str: Валідований UUID файлу

        Raises:
            ValidationError: Якщо UUID невалідний
        """
        if not file_uuid:
            raise ValidationError(_('UUID файлу не може бути порожнім'))

        if not cls.UUID_PATTERN.match(file_uuid):
            raise ValidationError(_('UUID файлу має невалідний формат'))

        try:
            uuid.UUID(file_uuid)
        except ValueError:
            raise ValidationError(_('UUID файлу має бути валідним'))

        return file_uuid

    @classmethod
    def validate_s3_key_format(cls, s3_key: str, expected_user_id: int, expected_gallery_url: str) -> bool:
        """
        Валідація формату S3 ключа.

        Args:
            s3_key: S3 ключ для валідації
            expected_user_id: Очікуваний ID користувача
            expected_gallery_url: Очікуваний Gallery URL події

        Returns:
            bool: True якщо ключ валідний

        Raises:
            ValidationError: Якщо ключ невалідний
        """
        if not s3_key:
            raise ValidationError(_('S3 ключ не може бути порожнім'))

        # Розбираємо шлях
        parts = s3_key.split('/')

        if len(parts) < 4:
            raise ValidationError(_('S3 ключ має невалідну структуру'))

        user_bucket, event_gallery_url, album_uuid, file_name = parts[:4]

        # Перевіряємо user bucket
        expected_bucket = f'user-bucket-{expected_user_id}'
        if user_bucket != expected_bucket:
            raise ValidationError(_('S3 ключ не належить даному користувачу'))

        # Перевіряємо event gallery URL
        if event_gallery_url != expected_gallery_url:
            raise ValidationError(_('S3 ключ не належить даній події'))

        # Валідуємо album UUID
        cls.validate_album_name(album_uuid)

        # Перевіряємо глибину шляху (захист від path traversal)
        if len(parts) > cls.MAX_PATH_DEPTH:
            raise ValidationError(_('Шлях занадто глибокий'))

        # Перевіряємо на небезпечні символи
        for part in parts:
            if '..' in part or part.startswith('.'):
                raise ValidationError(_('Шлях містить небезпечні символи'))

        return True

    @classmethod
    def validate_file_type(cls, file_type: str) -> str:
        """
        Валідація типу файлу.

        Args:
            file_type: MIME тип файлу

        Returns:
            str: Валідований тип файлу

        Raises:
            ValidationError: Якщо тип файлу не підтримується
        """
        if not file_type:
            raise ValidationError(_('Тип файлу не може бути порожнім'))

        # Дозволені MIME типи
        allowed_types = {
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
        }

        if file_type not in allowed_types:
            raise ValidationError(
                _('Непідтримуваний тип файлу: %(file_type)s. Дозволені типи: %(allowed_types)s')
                % {'file_type': file_type, 'allowed_types': ', '.join(sorted(allowed_types))}
            )

        return file_type

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Очищення та валідація імені файлу.

        Args:
            filename: Ім'я файлу для очищення

        Returns:
            str: Очищене ім'я файлу

        Raises:
            ValidationError: Якщо ім'я файлу невалідне
        """
        if not filename:
            raise ValidationError(_("Ім'я файлу не може бути порожнім"))

        # Видаляємо небезпечні символи
        filename = filename.strip()

        if len(filename) > cls.MAX_FILENAME_LENGTH:
            raise ValidationError(_("Ім'я файлу занадто довге"))

        # Перевіряємо на небезпечні шляхи
        if '..' in filename or filename.startswith('.'):
            raise ValidationError(_("Ім'я файлу містить небезпечні символи"))

        # Перевіряємо дозволені символи (можна розширити)
        if not re.match(r'^[a-zA-Z0-9\-_\.\s]+$', filename):
            raise ValidationError(_("Ім'я файлу містить недозволені символи"))

        return filename


class FileUploadValidator:
    """Валідатор для завантаження файлів"""

    # Максимальні розміри файлів (в байтах)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def validate_file_size(cls, file_type: str, file_size: int) -> bool:
        """
        Валідація розміру файлу за типом.

        Args:
            file_type: MIME тип файлу
            file_size: Розмір файлу в байтах

        Returns:
            bool: True якщо розмір валідний

        Raises:
            ValidationError: Якщо файл занадто великий
        """
        if file_size <= 0:
            raise ValidationError(_('Розмір файлу має бути більше 0'))

        if file_type.startswith('image/'):
            max_size = cls.MAX_IMAGE_SIZE
            file_category = _('зображення')
        elif file_type.startswith('video/'):
            max_size = cls.MAX_VIDEO_SIZE
            file_category = _('відео')
        elif file_type.startswith('application/'):
            max_size = cls.MAX_DOCUMENT_SIZE
            file_category = _('документ')
        else:
            raise ValidationError(_('Невідомий тип файлу'))

        if file_size > max_size:
            max_size_mb = max_size // (1024 * 1024)
            raise ValidationError(
                _('Файл %(category)s занадто великий. Максимальний розмір: %(max_size)d MB')
                % {'category': file_category, 'max_size': max_size_mb}
            )

        return True


