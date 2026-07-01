import logging
import os
import uuid

from django.db import transaction

from apps.accounts.models import CustomUser
from apps.albums.models import Album
from apps.events.models import Event
from apps.events.services.permission_service import EventPermissionService
from apps.mediafiles.dal.media_file_dal import MediaFileDAL
from apps.mediafiles.exceptions import AlbumNotFoundForMediaError
from apps.mediafiles.exceptions import FileOwnershipError
from apps.mediafiles.exceptions import MediaFilePermissionError
from apps.mediafiles.exceptions import UnsupportedFileTypeError
from apps.mediafiles.services.media_file_s3_service import MediaFileS3Service
from apps.mediafiles.tasks import cleanup_media_file_s3_task
from apps.mediafiles.tasks import generate_thumbnail_task
from apps.mediafiles.utils.thumbnail import derive_thumbnail_key
from apps.mediafiles.utils.thumbnail import is_image_mime_type
from apps.shared.utils.uuid_utils import S3KeyGenerator

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = [
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
    'audio/mpeg',
    'application/octet-stream',
]


class MediaFileService:
    """Service for media file business logic operations."""

    def __init__(
        self,
        dal: MediaFileDAL,
        s3_service: MediaFileS3Service,
        permission_service: EventPermissionService,
    ):
        self.dal = dal
        self.s3_service = s3_service
        self.permission_service = permission_service

    def generate_upload_url(
        self, user_id: int, event_uuid: str, album_uuid: str, file_name: str, content_type: str
    ) -> dict:
        """Generate presigned upload URL for a new file."""
        event = self._get_event_with_access_check(event_uuid, user_id)
        album = self._get_album_for_event(album_uuid, event)
        user = self._get_user(user_id)

        self._validate_file_type(content_type)

        file_uuid = uuid.uuid4()
        file_ext = os.path.splitext(file_name)[1] if file_name else ''

        s3_key = S3KeyGenerator.generate_file_key(
            user_uuid=str(user.user_uuid),
            event_uuid=str(event.event_uuid),
            album_uuid=str(album.album_uuid),
            file_uuid=str(file_uuid),
            file_extension=file_ext,
        )

        presigned_post = self.s3_service.generate_upload_url(s3_key, content_type)

        logger.info('Generated upload URL for event %s, album %s, user %s', event_uuid, album_uuid, user_id)
        return {
            'url': presigned_post['url'],
            'fields': presigned_post['fields'],
            's3_key': s3_key,
            'file_uuid': str(file_uuid),
            'event_uuid': str(event.event_uuid),
            'album_uuid': str(album.album_uuid),
            'expires_in': 3600,
        }

    def get_files_for_event(self, event_uuid: str, user_id: int) -> list[dict]:
        """Get all media files for an event."""
        event = self._get_event_with_access_check(event_uuid, user_id)
        files = self.dal.get_files_for_event(event)
        return [self._serialize_file(f) for f in files]

    def get_user_files(self, user_id: int) -> list[dict]:
        """Get all media files owned by a user."""
        files = self.dal.get_files_for_user(user_id)
        return [self._serialize_file(f) for f in files]

    def generate_download_url(self, file_uuid: str, user_id: int) -> dict:
        """Generate presigned download URL for a file."""
        media_file = self.dal.get_by_uuid_with_relations(file_uuid)
        self._validate_file_access(media_file, user_id)

        download_url = self.s3_service.generate_download_url(
            s3_key=media_file.S3_object_key,
            filename=media_file.file_name or None,
        )

        logger.info('Generated download URL for file %s, user %s', file_uuid, user_id)
        return {
            'download_url': download_url,
            'file_name': media_file.file_name,
            'expires_in': 3600,
        }

    def get_file_metadata(self, file_uuid: str, user_id: int) -> dict:
        """Get metadata for a file from DB record."""
        media_file = self.dal.get_by_uuid_with_relations(file_uuid)
        self._validate_file_access(media_file, user_id)
        return self._serialize_file(media_file)

    def update_file_metadata(self, file_uuid: str, user_id: int, metadata: dict) -> dict:
        """Update file metadata (file_name only)."""
        media_file = self.dal.get_by_uuid_with_relations(file_uuid)

        if media_file.user_id_id != user_id:
            raise FileOwnershipError(action='update')

        update_data = {}
        if 'file_name' in metadata:
            update_data['file_name'] = metadata['file_name']

        if update_data:
            media_file = self.dal.update(media_file, update_data)

        logger.info('Updated metadata for file %s, user %s', file_uuid, user_id)
        return self._serialize_file(media_file)

    @transaction.atomic
    def delete_file(self, file_uuid: str, user_id: int) -> None:
        """Delete a file from the DB and, only after commit, from S3.

        The DB row is deleted inside the transaction; the irreversible S3
        delete(s) fire via ``transaction.on_commit`` so a rolled-back delete
        never destroys the underlying object (rule #6).
        """
        media_file = self.dal.get_by_uuid_with_relations(file_uuid)

        if media_file.user_id_id != user_id:
            raise FileOwnershipError(action='delete')

        object_key = media_file.S3_object_key
        thumbnail_key = derive_thumbnail_key(object_key) if is_image_mime_type(media_file.file_type) else None

        self.dal.delete(media_file)

        transaction.on_commit(lambda: cleanup_media_file_s3_task.delay(object_key, thumbnail_key))
        logger.info('Deleted file %s by user %s', file_uuid, user_id)

    def process_uploaded_file_by_uuid(
        self,
        event_uuid: str,
        user_id: int,
        s3_key: str,
        file_type: str,
        file_uuid: str | None = None,
        album_uuid: str | None = None,
        file_name: str | None = None,
    ) -> dict:
        """Process uploaded file: create DB record and run post-upload tasks."""
        event = self._get_event_with_access_check(event_uuid, user_id)

        if not self._validate_file_access_by_key(s3_key, user_id, event):
            raise MediaFilePermissionError(action='confirm_upload')

        album = self._resolve_album(event, album_uuid, s3_key)
        if not album:
            raise AlbumNotFoundForMediaError()

        if not file_name:
            file_name = os.path.basename(s3_key)

        # Fetch the real size from S3 (head_object). Failure is non-fatal —
        # the file row is still useful with size=0; the backfill command can
        # repair it later.
        file_size = 0
        try:
            metadata = self.s3_service.get_metadata(s3_key)
            file_size = int(metadata.get('content_length') or 0)
        except Exception:
            logger.exception('Could not fetch S3 ContentLength for %s', s3_key)

        media_file = self.dal.create({
            'file_uuid': file_uuid or uuid.uuid4(),
            'file_name': file_name,
            'album_id': album,
            'user_id_id': user_id,
            'file_type': file_type,
            'file_size': file_size,
            'S3_bucket_name': self.s3_service.bucket_name,
            'S3_object_key': s3_key,
        })

        logger.info(
            'Created MediaFile %s for album %s, user %s (size=%s bytes)',
            media_file.file_uuid,
            album.album_uuid,
            user_id,
            file_size,
        )

        if is_image_mime_type(file_type):
            generate_thumbnail_task.delay(str(media_file.file_uuid))
            logger.info('Dispatched thumbnail generation for %s', media_file.file_uuid)

        return {
            'file_uuid': str(media_file.file_uuid),
            'file_name': media_file.file_name,
            's3_key': media_file.S3_object_key,
            'album_uuid': str(album.album_uuid),
            'status': 'processed',
        }

    def _serialize_file(self, media_file) -> dict:
        """Serialize a MediaFile instance to dict."""
        album = media_file.album_id
        thumbnail_url = None
        if is_image_mime_type(media_file.file_type):
            try:
                thumbnail_key = derive_thumbnail_key(media_file.S3_object_key)
                thumbnail_url = self.s3_service.generate_thumbnail_url(thumbnail_key)
            except Exception:
                logger.debug('Could not generate thumbnail URL for %s', media_file.file_uuid)

        return {
            'file_uuid': str(media_file.file_uuid),
            'file_name': media_file.file_name,
            'file_type': media_file.file_type,
            'file_size': media_file.file_size,
            's3_key': media_file.S3_object_key,
            'album_uuid': str(album.album_uuid) if album else None,
            'created_at': media_file.created_at.isoformat() if media_file.created_at else None,
            'thumbnail_url': thumbnail_url,
        }

    def _get_event_with_access_check(self, event_uuid: str, user_id: int) -> Event:
        """Get event by UUID and validate user access."""
        try:
            event = Event.objects.prefetch_related(
                'participants_through__user',
            ).get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            from apps.events.exceptions import EventNotFoundError

            raise EventNotFoundError(str(event_uuid))

        if not self.permission_service.has_event_access(event, user_id):
            raise MediaFilePermissionError(action='access_event')

        return event

    def _get_album_for_event(self, album_uuid: str, event: Event) -> Album:
        """Get album by UUID and verify it belongs to the event."""
        try:
            return Album.objects.get(album_uuid=album_uuid, event=event)
        except Album.DoesNotExist:
            raise AlbumNotFoundForMediaError(str(album_uuid))

    def _get_album(self, album_pk: int) -> Album:
        """Get album by PK with related event."""
        try:
            return Album.objects.select_related('event').get(pk=album_pk)
        except Album.DoesNotExist:
            raise AlbumNotFoundForMediaError()

    def _get_user(self, user_id: int) -> CustomUser:
        """Get user by ID."""
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            from apps.shared.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError('User not found', error_code='user_not_found')

    def _validate_file_access(self, media_file, user_id: int) -> None:
        """Check if user can access a file (owner or event participant)."""
        if media_file.user_id_id == user_id:
            return

        event = media_file.album_id.event
        if self.permission_service.has_event_access(event, user_id):
            return

        raise MediaFilePermissionError(action='access_file')

    def _validate_file_access_by_key(self, s3_key: str, user_id: int, event: Event) -> bool:
        """Validate that an S3 key belongs to both the event and the requester.

        Matching only the event is not enough: keys embed the owner's
        ``user_uuid``, so an event participant could otherwise confirm a key
        under another user's prefix in the same (e.g. public) event.
        """
        if s3_key.startswith('users/'):
            parsed = S3KeyGenerator.parse_s3_key(s3_key)
            user = self._get_user(user_id)
            return parsed.get('event_uuid') == str(event.event_uuid) and parsed.get('user_uuid') == str(user.user_uuid)
        return s3_key.startswith(f'user-bucket-{user_id}/{event.event_uuid}/')

    def _validate_file_type(self, file_type: str) -> None:
        """Validate file MIME type."""
        if file_type not in ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(file_type)

    def _resolve_album(self, event: Event, album_uuid: str | None, s3_key: str) -> Album | None:
        """Resolve album from album_uuid or from s3_key, with fallback."""
        if album_uuid:
            try:
                return Album.objects.get(album_uuid=album_uuid, event=event)
            except Album.DoesNotExist:
                logger.warning('Album %s not found for event %s', album_uuid, event.event_uuid)

        parsed = S3KeyGenerator.parse_s3_key(s3_key)
        if parsed.get('album_uuid'):
            try:
                return Album.objects.get(album_uuid=parsed['album_uuid'], event=event)
            except Album.DoesNotExist:
                pass

        return Album.objects.filter(event=event).first()
