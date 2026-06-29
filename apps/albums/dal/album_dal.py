import logging

from django.db.models import QuerySet

from apps.albums.models import Album
from apps.shared.decorators.database import handle_db_errors

logger = logging.getLogger(__name__)


class AlbumDAL:
    """Data Access Layer for Album operations."""

    @handle_db_errors(model_name='Album')
    def get_by_uuid_with_relations(self, album_uuid) -> Album:
        """Get album by UUID with related event and owner participants pre-loaded."""
        return (
            Album.objects.select_related('event')
            .prefetch_related('event__participants_through__user')
            .get(album_uuid=album_uuid)
        )

    @handle_db_errors(model_name='Album')
    def get_albums_for_event(self, event_id) -> QuerySet:
        """Get all albums for a specific event with file_count annotation."""
        return Album.objects.for_event(event_id).select_related('event').with_file_counts()

    @handle_db_errors(model_name='Album')
    def create(self, **data) -> Album:
        """Create a new album."""
        return Album.objects.create(**data)

    @handle_db_errors(model_name='Album')
    def update(self, album: Album, data: dict) -> Album:
        """Update album fields."""
        for field, value in data.items():
            if hasattr(album, field):
                setattr(album, field, value)
        album.save()
        return album

    @handle_db_errors(model_name='Album')
    def delete(self, album: Album) -> bool:
        """Delete album instance."""
        album.delete()
        return True
