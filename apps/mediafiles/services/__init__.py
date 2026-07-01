"""
MediaFiles Services Package

This package contains all services for working with media files:
- MediaFileService: Main service for media file business logic (DI-based)
- MediaFileS3Service: S3 presigned URL operations
"""

from apps.mediafiles.services.media_file_s3_service import MediaFileS3Service
from apps.mediafiles.services.media_file_service import MediaFileService

# Backward compatibility alias
MediafileService = MediaFileService

__all__ = [
    'MediaFileService',
    'MediaFileS3Service',
    'MediafileService',
]
