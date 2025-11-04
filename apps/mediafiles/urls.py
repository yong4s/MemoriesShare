from django.urls import path

from .views import FileBulkDownloadUrlsAPIView
from .views import FileDeleteAPIView
from .views import FileDownloadUrlAPIView
from .views import FileMetadataAPIView
from .views import FileUploadedAPIView
from .views import FileUploadUrlAPIView
from .views import GalleryUploadUrlAPIView
from .views import MediaFileDeleteView
from .views import MediaFileDetailView
from .views import MediaFileListCreateView
from .views import MediaFileUpdateView

# urlpatterns = [
#     path('upload/<int:album_pk>/', MediaFileUploadView.as_view(), name='file-upload'),

# ]

urlpatterns = [
    # Existing MediaFile CRUD operations
    path('albums/<int:album_pk>/mediafiles/', MediaFileListCreateView.as_view(), name='mediafile-list-create'),
    path('<int:pk>/', MediaFileDetailView.as_view(), name='mediafile-detail'),
    path('<int:pk>/update/', MediaFileUpdateView.as_view(), name='mediafile-update'),
    path('<int:pk>/delete/', MediaFileDeleteView.as_view(), name='mediafile-delete'),
    # File operations (moved from Events app)
    path('upload/<str:event_gallery_url>/', GalleryUploadUrlAPIView.as_view(), name='gallery-upload'),
    # File operations by event UUID
    path('files/upload/', FileUploadUrlAPIView.as_view(), name='file-upload-url'),
    path('files/download/', FileDownloadUrlAPIView.as_view(), name='file-download-url'),
    path('files/bulk-download/', FileBulkDownloadUrlsAPIView.as_view(), name='file-bulk-download-urls'),
    path('files/delete/', FileDeleteAPIView.as_view(), name='file-delete'),
    path('files/<str:event_uuid>/metadata/', FileMetadataAPIView.as_view(), name='file-metadata'),
    path('files/uploaded/', FileUploadedAPIView.as_view(), name='file-uploaded'),
]
