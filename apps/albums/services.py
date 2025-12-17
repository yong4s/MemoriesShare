"""
Albums Services Package

For backward compatibility all services are available through this file.
- AlbumService: apps.albums.services.album_service
"""

from apps.albums.services.album_service import AlbumService

__all__ = [
    'AlbumService',
]
