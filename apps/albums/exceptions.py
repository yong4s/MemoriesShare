"""
Domain-specific business exceptions for Albums app.

Following Clean Architecture principles:
- These are BUSINESS exceptions, not HTTP exceptions
- They represent domain logic failures
- HTTP mapping happens in the global exception handler
- Inherits from core business exception hierarchy
"""

from apps.shared.exceptions import PermissionError


class AlbumPermissionError(PermissionError):
    """Raised when user lacks permission to access/modify album."""

    def __init__(self, action: str | None = None, album_id: str | None = None, **kwargs):
        if action and album_id:
            message = f"Permission denied for '{action}' on album '{album_id}'"
        else:
            message = 'Permission denied for this album operation'
        super().__init__(message, error_code='album_permission_denied', **kwargs)
