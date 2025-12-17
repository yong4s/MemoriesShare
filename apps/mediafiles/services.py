"""
MediaFiles Services Package

For backward compatibility all services are available through this file.
New architecture separates services into individual modules:
- MediafileService: apps.mediafiles.services.mediafile_service
"""

from apps.mediafiles.services.mediafile_service import MediafileService

__all__ = [
    'MediafileService',
]
