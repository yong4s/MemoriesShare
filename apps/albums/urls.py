from django.urls import path

from apps.albums.views import AlbumCreateApiView
from apps.albums.views import AlbumDeleteApiView
from apps.albums.views import AlbumListApiView

urlpatterns = [
    # Album CRUD operations
    path('', AlbumListApiView.as_view(), name='album-list'),  # GET /albums/
    path('create/', AlbumCreateApiView.as_view(), name='album-create'),  # POST /albums/create/
    path('<uuid:album_uuid>/', AlbumDeleteApiView.as_view(), name='album-delete'),  # DELETE /albums/{uuid}/
    # Event-specific albums (moved from events app)
    path('event/<uuid:event_uuid>/', AlbumListApiView.as_view(), name='event-album-list'),  # GET /albums/event/{uuid}/
]
