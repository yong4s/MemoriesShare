import logging

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.accounts.exceptions import InvalidUserIdError
from apps.albums.dal import AlbumDAL
from apps.albums.models import Album
from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.storage.optimized_s3_service import OptimizedS3Service
from apps.shared.utils.general import get_user_by_id

logger = logging.getLogger(__name__)


class AlbumService:
    """Service for album business logic operations."""

    def __init__(self):
        """Initialize service with dependencies."""
        self.s3service = OptimizedS3Service()
        self.dal = AlbumDAL()

    def create_album(self, serializer, event, user_id):
        """Create album for event with permission validation and S3 integration."""
        if not user_id or not event:
            logger.warning(f'Album creation attempt with invalid parameters: user_id={user_id}, event={event}')
            msg = 'You do not have permission to add albums to this event.'
            raise PermissionDenied(msg)

        try:
            user = get_user_by_id(user_id)
        except InvalidUserIdError:
            logger.exception(f'Invalid user ID provided for album creation: {user_id}')
            raise

        # Check if user is event owner
        if event.user_id != user_id:
            logger.warning(f'User {user_id} attempted to create album for event {event.id} without ownership')
            msg = 'Only event owner can create albums.'
            raise PermissionDenied(msg)

        # Create album object without saving to DB first
        album = Album(
            event=event,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_public=serializer.validated_data.get('is_public', False),
        )

        # Generate S3 prefix before saving: users/{user_uuid}/events/{event_uuid}/albums/{album_uuid}
        album_folder_name = f'users/{user.user_uuid}/events/{event.event_uuid}/albums/{album.album_uuid}'
        album.album_s3_prefix = album_folder_name

        try:
            logger.info(f'Creating S3 folder: {album_folder_name}')
            result = self.s3service.create_folder(album_folder_name)
            logger.info(f'S3 folder creation result: {result}')

            # Check if result contains error
            if 'Error' in str(result):
                msg = f'S3 folder creation failed: {result}'
                raise Exception(msg)

            # Save to DB only AFTER successful S3 folder creation
            album.save()
            logger.info(f'Album {album.album_uuid} created successfully with S3 prefix: {album_folder_name}')

        except Exception as e:
            # S3 folder creation failed - don't save to DB at all
            logger.exception(f'Failed to create S3 folder for album: {e!s}')
            msg = f'Failed to create album folder: {e!s}'
            raise S3ServiceError(msg)

        return album

    def get_album(self, user_id, album_id):
        album = self.dal.get_album_by_id(album_id)

        if not self._is_owner_or_guest(album.event_id, user_id):
            logger.warning(f'User {user_id} attempted to access album {album_id} without permission')
            msg = 'You do not have permission to view this album.'
            raise PermissionDenied(msg)

        return album

    def get_albums_for_event(self, user_id, event_id):
        if not self._is_owner_or_guest(event_id, user_id):
            logger.warning(f'User {user_id} attempted to access albums for event {event_id} without permission')
            msg = 'You do not have permission to view albums for this event.'
            raise PermissionDenied(msg)

        return self.dal.get_all_event_albums(event_id)

    def update_album(self, user_id, album_id, album_data):
        """Update album with owner permission check."""
        album = self.dal.get_album_by_id(album_id)

        # Check if user is event owner
        if album.event.user_id != user_id:
            logger.warning(f'User {user_id} attempted to update album {album_id} without ownership')
            msg = 'Only event owner can update albums.'
            raise PermissionDenied(msg)

        # Update album fields
        for field, value in album_data.items():
            if hasattr(album, field):
                setattr(album, field, value)

        album.save()
        logger.info(f'Album {album_id} updated successfully by user {user_id}')

        return album

    def delete_album(self, user_id, album_id):
        """Delete album with S3 cleanup and permission check."""
        album = self.dal.get_album_by_id(album_id)

        # Check if user is event owner
        if album.event.user_id != user_id:
            logger.warning(f'User {user_id} attempted to delete album {album_id} without ownership')
            msg = 'You do not have permission to delete albums for this event.'
            raise PermissionDenied(msg)

        album_folder_url = album.album_s3_prefix

        try:
            # First delete S3 structure
            if album_folder_url:
                logger.info(f'Deleting S3 folder: {album_folder_url}')
                self.s3service.delete_folder(album_folder_url)
                logger.info(f'S3 folder deleted successfully: {album_folder_url}')
        except Exception as e:
            logger.exception(f'Failed to delete S3 folder for album {album_id}: {e!s}')
            msg = f'Failed to delete album folder: {e!s}'
            raise S3ServiceError(msg)

        # Then delete from DB
        result = self.dal.delete_album(album_id)
        logger.info(f'Album {album_id} deleted successfully by user {user_id}')

        return result

    def _is_owner_or_guest(self, event_id, user_id):
        """Check if user is event owner or guest."""
        try:
            # Simple approach: get any album for this event to check permissions
            albums = self.dal.get_all_event_albums(event_id)
            if not albums:
                return False

            # Check if user is event owner through album's event relationship
            return albums[0].event.user_id == user_id
        except:
            return False

    def get_album_statistics(self, album_id, user_id):
        """Get album statistics including file count and total size."""
        album = self.get_album(user_id, album_id)

        # Get statistics through DAL
        stats = self.dal.get_album_statistics(album_id)

        return {
            'album_id': album_id,
            'album_name': album.name,
            'total_files': stats.get('file_count', 0),
            'total_size_bytes': stats.get('total_size', 0),
            'created_at': album.created_at,
            'last_modified': album.updated_at,
            'is_public': album.is_public,
        }
