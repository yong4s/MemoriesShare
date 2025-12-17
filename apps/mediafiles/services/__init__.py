"""
MediaFiles Services Package

This package contains all services for working with media files:
- MediafileService: Main service for CRUD operations with media files
"""

from apps.mediafiles.services.mediafile_service import MediafileService

__all__ = [
    'MediafileService',
]
