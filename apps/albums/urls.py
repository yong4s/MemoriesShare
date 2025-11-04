from django.urls import path

from apps.albums.views import AlbumCreateApiView
from apps.albums.views import AlbumDeleteApiView
from apps.albums.views import AlbumListApiView
from apps.mediafiles.views import MediaFileDeleteView
from apps.mediafiles.views import MediaFileDetailView
from apps.mediafiles.views import MediaFileListCreateView
from apps.mediafiles.views import MediaFileUpdateView

urlpatterns = [
    # Album CRUD operations
    path('', AlbumListApiView.as_view(), name='album-list'),  # GET /albums/
    path('create/', AlbumCreateApiView.as_view(), name='album-create'),  # POST /albums/create/
    path('<uuid:album_uuid>/', AlbumDeleteApiView.as_view(), name='album-delete'),  # DELETE /albums/{uuid}/
    # Event-specific albums (moved from events app)
    path('event/<uuid:event_uuid>/', AlbumListApiView.as_view(), name='event-album-list'),  # GET /albums/event/{uuid}/
    # Media files - should be moved to mediafiles app
    path('<int:album_pk>/mediafiles/', MediaFileListCreateView.as_view(), name='mediafile-list-create'),
    path('mediafiles/<int:pk>/', MediaFileDetailView.as_view(), name='mediafile-detail'),
    path('mediafiles/<int:pk>/update/', MediaFileUpdateView.as_view(), name='mediafile-update'),
    path('mediafiles/<int:pk>/delete/', MediaFileDeleteView.as_view(), name='mediafile-delete'),
]
