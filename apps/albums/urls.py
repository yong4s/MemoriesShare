from django.urls import path

from apps.albums.views import AlbumAPIView
from apps.albums.views import AlbumListApiView

urlpatterns = [
    path(
        'event/<uuid:event_uuid>/',
        AlbumListApiView.as_view(),
        name='album-list',
    ),
    path(
        '<uuid:album_uuid>/',
        AlbumAPIView.as_view(),
        name='album-detail',
    ),
]
