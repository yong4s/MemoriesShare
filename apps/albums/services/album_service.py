from __future__ import annotations

import logging

from django.db import transaction

from apps.albums.cache.album_cache_service import album_cache_service as default_album_cache
from apps.albums.cache.album_cache_service import AlbumCacheService
from apps.albums.dal.album_dal import AlbumDAL
from apps.albums.exceptions import AlbumPermissionError
from apps.albums.models import Album
from apps.albums.tasks import cleanup_album_s3_prefix_task
from apps.events.services.permission_service import EventPermissionService

logger = logging.getLogger(__name__)


class AlbumService:
    """Service for album business logic operations with constructor DI."""

    def __init__(
        self,
        dal: AlbumDAL,
        permission_service: EventPermissionService,
        cache_service: AlbumCacheService | None = None,
    ):
        self.dal = dal
        self.permission_service = permission_service
        self.cache_service = cache_service or default_album_cache

    @transaction.atomic
    def create_album(self, event, user_id, name, description='', is_public=False):
        """Create album for event with permission validation.

        S3 prefix is stored in DB but no S3 folder is created —
        the path materializes automatically when the first file is uploaded.
        """
        if not self.permission_service.is_event_owner(event, user_id):
            logger.warning(f'User {user_id} attempted to create album for event {event.id} without ownership')
            raise AlbumPermissionError(action='create', album_id=str(event.event_uuid))

        album = Album(
            event=event,
            name=name,
            description=description,
            is_public=is_public,
        )

        album.album_s3_prefix = f'{event.s3_prefix}/albums/{album.album_uuid}'

        album.save()
        logger.info(f'Album {album.album_uuid} created with S3 prefix: {album.album_s3_prefix}')

        self._schedule_album_invalidation(
            album_uuid=album.album_uuid,
            event_uuid=event.event_uuid,
        )

        return album

    def get_album_detail(self, album_uuid, user_id):
        """Get album detail with permission check."""
        album = self.dal.get_by_uuid_with_relations(album_uuid)

        if not self._can_view_album(album, user_id):
            logger.warning(f'User {user_id} attempted to access album {album_uuid} without permission')
            raise AlbumPermissionError(action='view', album_id=str(album_uuid))

        return album

    def get_albums_for_event(self, event, user_id):
        """Get albums for an event.

        Participants (any role) see every album; non-participants see only albums
        explicitly marked public, and are denied if the event has none for them.
        """
        albums = self.dal.get_albums_for_event(event.id)

        if self.permission_service.is_user_participant(event, user_id):
            return albums

        public_albums = [album for album in albums if album.is_public]
        if not public_albums:
            logger.warning(f'User {user_id} attempted to access albums for event {event.id} without permission')
            raise AlbumPermissionError(action='view', album_id=str(event.event_uuid))
        return public_albums

    @transaction.atomic
    def update_album(self, album_uuid, album_data, user_id):
        """Update album with owner permission check."""
        album = self.dal.get_by_uuid_with_relations(album_uuid)

        if not self.permission_service.is_event_owner(album.event, user_id):
            logger.warning(f'User {user_id} attempted to update album {album_uuid} without ownership')
            raise AlbumPermissionError(action='update', album_id=str(album_uuid))

        updated_album = self.dal.update(album, album_data)
        logger.info(f'Album {album_uuid} updated successfully by user {user_id}')

        self._schedule_album_invalidation(
            album_uuid=updated_album.album_uuid,
            event_uuid=updated_album.event.event_uuid,
        )

        return updated_album

    @transaction.atomic
    def delete_album(self, album_uuid, user_id):
        """Delete album; S3 cleanup runs in Celery after commit."""
        album = self.dal.get_by_uuid_with_relations(album_uuid)

        if not self.permission_service.is_event_owner(album.event, user_id):
            logger.warning(f'User {user_id} attempted to delete album {album_uuid} without ownership')
            raise AlbumPermissionError(action='delete', album_id=str(album_uuid))

        s3_prefix = album.album_s3_prefix
        album_uuid_str = str(album.album_uuid)
        event_uuid_str = str(album.event.event_uuid)

        self.dal.delete(album)
        logger.info(f'Album {album_uuid} deleted by user {user_id}; S3 cleanup scheduled')

        transaction.on_commit(
            lambda: cleanup_album_s3_prefix_task.delay(s3_prefix, album_uuid_str),
        )
        self._schedule_album_invalidation(
            album_uuid=album_uuid_str,
            event_uuid=event_uuid_str,
        )

    def _schedule_album_invalidation(self, album_uuid, event_uuid) -> None:
        """Register post-commit cache invalidation so readers don't see stale album data."""
        album_uuid_str = str(album_uuid)
        event_uuid_str = str(event_uuid)

        def _invalidate() -> None:
            try:
                self.cache_service.invalidate_album(album_uuid_str)
                self.cache_service.invalidate_event_albums(event_uuid_str)
            except Exception as exc:
                logger.warning(
                    'Album cache invalidation failed for album %s event %s: %s',
                    album_uuid_str,
                    event_uuid_str,
                    exc,
                )

        transaction.on_commit(_invalidate)

    def _can_view_album(self, album, user_id) -> bool:
        """Whether a user may view an album.

        album.is_public is the authoritative public-access gate: a private album is
        NOT exposed just because its event is public, and event participants (any
        role) always see every album of their event.
        """
        return album.is_public or self.permission_service.is_user_participant(album.event, user_id)
