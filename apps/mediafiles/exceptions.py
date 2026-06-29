"""
Domain-specific business exceptions for MediaFiles app.

Following Clean Architecture principles:
- These are BUSINESS exceptions, not HTTP exceptions
- They represent domain logic failures
- HTTP mapping happens in the global exception handler
- Inherits from core business exception hierarchy
"""

from apps.shared.exceptions import BusinessRuleViolation
from apps.shared.exceptions import PermissionError
from apps.shared.exceptions import ResourceNotFoundError
from apps.shared.exceptions import ValidationError


class MediaFileNotFoundError(ResourceNotFoundError):
    """Raised when requested media file does not exist."""

    def __init__(self, file_identifier: str | None = None, **kwargs):
        message = 'Media file not found'
        if file_identifier:
            message = f"Media file '{file_identifier}' not found"
        super().__init__(message, error_code='media_file_not_found', **kwargs)


class MediaFilePermissionError(PermissionError):
    """Raised when user lacks permission to access/modify media file."""

    def __init__(self, action: str | None = None, file_id: str | None = None, **kwargs):
        if action and file_id:
            message = f"Permission denied for '{action}' on media file '{file_id}'"
        else:
            message = 'Permission denied for this media file operation'
        super().__init__(message, error_code='media_file_permission_denied', **kwargs)


class MediaFileValidationError(ValidationError):
    """Raised when media file data fails business validation."""

    def __init__(self, message: str = 'Media file validation failed', **kwargs):
        super().__init__(message, error_code='media_file_validation_error', **kwargs)


class MediaFileStorageError(BusinessRuleViolation):
    """Raised when S3 storage operation fails."""

    def __init__(self, operation: str, details: str | None = None, **kwargs):
        message = f'Storage operation failed: {operation}'
        if details:
            message = f'{message}. {details}'
        super().__init__(message, error_code=f'media_storage_{operation}_failed', **kwargs)


class AlbumNotFoundForMediaError(ResourceNotFoundError):
    """Raised when album for media upload does not exist."""

    def __init__(self, album_identifier: str | None = None, **kwargs):
        message = 'Album not found for this upload'
        if album_identifier:
            message = f"Album '{album_identifier}' not found for this event"
        super().__init__(message, error_code='album_not_found_for_media', **kwargs)


class UnsupportedFileTypeError(MediaFileValidationError):
    """Raised when file type is not in the allowed list."""

    def __init__(self, file_type: str, **kwargs):
        message = f'Unsupported file type: {file_type}'
        super().__init__(message, **kwargs)


class FileOwnershipError(MediaFilePermissionError):
    """Raised when non-owner tries to modify/delete a file."""

    def __init__(self, action: str = 'modify', **kwargs):
        super().__init__(action=action, **kwargs)
