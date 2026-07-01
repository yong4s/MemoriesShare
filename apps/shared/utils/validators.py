"""
Validators for safe handling of files and S3 keys.
"""

import re
import uuid

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class S3KeyValidator:
    """Validator for S3 keys and safe paths."""

    # Characters allowed in file and folder names
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_\.]+$')
    UUID_PATTERN = re.compile(r'^[a-f0-9\-]{36}$')
    ALBUM_UUID_PATTERN = re.compile(r'^[a-f0-9\-]{36}$')

    MAX_FILENAME_LENGTH = 255
    MAX_PATH_DEPTH = 10

    @classmethod
    def validate_album_name(cls, album_name: str) -> str:
        """
        Validate the album name (must be a UUID).

        Args:
            album_name: Album name to validate

        Returns:
            str: Validated album name

        Raises:
            ValidationError: If the album name is invalid
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
        Validate a file UUID.

        Args:
            file_uuid: File UUID to validate

        Returns:
            str: Validated file UUID

        Raises:
            ValidationError: If the UUID is invalid
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
        Validate the format of an S3 key.

        Args:
            s3_key: S3 key to validate
            expected_user_id: Expected user ID
            expected_gallery_url: Expected event gallery URL

        Returns:
            bool: True if the key is valid

        Raises:
            ValidationError: If the key is invalid
        """
        if not s3_key:
            raise ValidationError(_('S3 ключ не може бути порожнім'))

        parts = s3_key.split('/')

        if len(parts) < 4:
            raise ValidationError(_('S3 ключ має невалідну структуру'))

        user_bucket, event_gallery_url, album_uuid, _file_name = parts[:4]

        expected_bucket = f'user-bucket-{expected_user_id}'
        if user_bucket != expected_bucket:
            raise ValidationError(_('S3 ключ не належить даному користувачу'))

        if event_gallery_url != expected_gallery_url:
            raise ValidationError(_('S3 ключ не належить даній події'))

        cls.validate_album_name(album_uuid)

        # Guard against path traversal via excessive depth
        if len(parts) > cls.MAX_PATH_DEPTH:
            raise ValidationError(_('Шлях занадто глибокий'))

        # Reject path traversal sequences and hidden-path components
        for part in parts:
            if '..' in part or part.startswith('.'):
                raise ValidationError(_('Шлях містить небезпечні символи'))

        return True

    @classmethod
    def validate_file_type(cls, file_type: str) -> str:
        """
        Validate the file type.

        Args:
            file_type: File MIME type

        Returns:
            str: Validated file type

        Raises:
            ValidationError: If the file type is not supported
        """
        if not file_type:
            raise ValidationError(_('Тип файлу не може бути порожнім'))

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
                % {
                    'file_type': file_type,
                    'allowed_types': ', '.join(sorted(allowed_types)),
                }
            )

        return file_type

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize and validate a filename.

        Args:
            filename: Filename to sanitize

        Returns:
            str: Sanitized filename

        Raises:
            ValidationError: If the filename is invalid
        """
        if not filename:
            raise ValidationError(_("Ім'я файлу не може бути порожнім"))

        filename = filename.strip()

        if len(filename) > cls.MAX_FILENAME_LENGTH:
            raise ValidationError(_("Ім'я файлу занадто довге"))

        # Reject path traversal sequences and hidden-path components
        if '..' in filename or filename.startswith('.'):
            raise ValidationError(_("Ім'я файлу містить небезпечні символи"))

        if not re.match(r'^[a-zA-Z0-9\-_\.\s]+$', filename):
            raise ValidationError(_("Ім'я файлу містить недозволені символи"))

        return filename
