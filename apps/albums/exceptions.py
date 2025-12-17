"""
Domain-specific exceptions for Albums app.

Following Clean Architecture principles, these exceptions are tightly coupled
to the albums business domain and reside within the albums app for high cohesion.
"""

from rest_framework.exceptions import APIException


class AlbumNotFoundError(APIException):
    """Exception raised when requested album does not exist."""

    status_code = 404
    default_detail = 'Album not found.'
    default_code = 'album_not_found'


class AlbumPermissionError(APIException):
    """Exception raised when user lacks permission to access/modify album."""

    status_code = 403
    default_detail = 'Permission denied for this album.'
    default_code = 'album_permission_denied'


class InvalidAlbumDataError(APIException):
    """Exception raised when album data validation fails."""

    status_code = 400
    default_detail = 'Invalid album data provided.'
    default_code = 'invalid_album_data'


class AlbumCreationError(APIException):
    """Exception raised when album creation fails due to business logic constraints."""

    status_code = 400
    default_detail = 'Error occurred while creating the album.'
    default_code = 'album_creation_error'


class AlbumDeletionError(APIException):
    """Exception raised when album deletion fails."""

    status_code = 400
    default_detail = 'Error occurred while deleting the album.'
    default_code = 'album_deletion_error'


class AlbumCapacityExceededError(APIException):
    """Exception raised when album file capacity is exceeded."""

    status_code = 400
    default_detail = 'Album file capacity exceeded.'
    default_code = 'album_capacity_exceeded'


class DuplicateAlbumError(APIException):
    """Exception raised when album with same name already exists for event."""

    status_code = 400
    default_detail = 'Album with this name already exists for this event.'
    default_code = 'duplicate_album'


class AlbumAccessError(APIException):
    """Exception raised when album access rules are violated."""

    status_code = 403
    default_detail = 'Album access denied based on current settings.'
    default_code = 'album_access_denied'


class AlbumStorageError(APIException):
    """Exception raised when album storage operations fail."""

    status_code = 500
    default_detail = 'Album storage operation failed.'
    default_code = 'album_storage_error'


class AlbumDownloadError(APIException):
    """Exception raised when album download operations fail."""

    status_code = 500
    default_detail = 'Album download operation failed.'
    default_code = 'album_download_error'


class InvalidAlbumEventError(APIException):
    """Exception raised when album is associated with invalid event."""

    status_code = 400
    default_detail = 'Album cannot be associated with this event.'
    default_code = 'invalid_album_event'
