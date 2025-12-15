from .models import Album


class AlbumDAL:
    def get_album_by_uuid(self, album_uuid):
        return Album.objects.get(album_uuid=album_uuid)

    def get_all_event_albums(self, event_uuid):
        """Отримує всі альбоми для конкретної події."""
        return Album.objects.filter(event_uuid=event_uuid)

    def delete_album(self, album_uuid):
        """Видаляє альбом за ID."""
        album = self.get_album_by_uuid(album_uuid)
        album.delete()

    def get_event_by_album_id(self, album_uuid):
        """Отримує подію (Event), до якої належить альбом."""
        album = Album.objects.filter(id=album_uuid).select_related("event").first()
        return album.event if album else None
