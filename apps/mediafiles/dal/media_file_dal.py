from typing import Any

from django.db.models import QuerySet

from apps.mediafiles.models import MediaFile
from apps.shared.decorators.database import handle_db_errors


class MediaFileDAL:
    """Data Access Layer for MediaFile model operations"""

    @handle_db_errors(operation_type='read', model_name='MediaFile')
    def get_by_uuid_with_relations(self, file_uuid: str) -> MediaFile:
        """Get media file with related album, event, and user"""
        return MediaFile.objects.select_related(
            'album_id',
            'album_id__event',
            'user_id',
        ).get(file_uuid=file_uuid)

    def get_files_for_event(self, event) -> QuerySet[MediaFile]:
        """Get all media files for an event"""
        return (
            MediaFile.objects.filter(album_id__event=event)
            .select_related('album_id')
            .order_by('-created_at')
        )

    def get_files_for_user(self, user_id: int) -> QuerySet[MediaFile]:
        """Get all media files owned by a user"""
        return (
            MediaFile.objects.filter(user_id=user_id)
            .select_related('album_id')
            .order_by('-created_at')
        )

    @handle_db_errors(operation_type='create', model_name='MediaFile')
    def create(self, media_file_data: dict[str, Any]) -> MediaFile:
        """Create a new media file record"""
        return MediaFile.objects.create(**media_file_data)

    @handle_db_errors(operation_type='update', model_name='MediaFile')
    def update(self, media_file: MediaFile, data: dict[str, Any]) -> MediaFile:
        """Update media file fields"""
        for field, value in data.items():
            setattr(media_file, field, value)
        media_file.save()
        return media_file

    @handle_db_errors(operation_type='delete', model_name='MediaFile')
    def delete(self, media_file: MediaFile) -> bool:
        """Delete a media file record"""
        media_file.delete()
        return True
