from django.urls import path

from apps.mediafiles.views import FileBulkDownloadUrlsAPIView
from apps.mediafiles.views import FileDeleteAPIView
from apps.mediafiles.views import FileDownloadUrlAPIView
from apps.mediafiles.views import FileMetadataAPIView
from apps.mediafiles.views import FileUploadedAPIView
from apps.mediafiles.views import FileUploadUrlAPIView
from apps.mediafiles.views import GalleryUploadUrlAPIView

# urlpatterns = [
#     path('upload/<int:album_pk>/', MediaFileUploadView.as_view(), name='file-upload'),

# ]

urlpatterns = [
    # S3 File Operations
    path(
        'upload/<str:event_gallery_url>/',
        GalleryUploadUrlAPIView.as_view(),
        name='gallery-upload',
    ),
    path('files/upload/', FileUploadUrlAPIView.as_view(), name='file-upload-url'),
    path('files/download/', FileDownloadUrlAPIView.as_view(), name='file-download-url'),
    path(
        'files/bulk-download/',
        FileBulkDownloadUrlsAPIView.as_view(),
        name='file-bulk-download-urls',
    ),
    path('files/delete/', FileDeleteAPIView.as_view(), name='file-delete'),
    path(
        'files/<str:event_uuid>/metadata/',
        FileMetadataAPIView.as_view(),
        name='file-metadata',
    ),
    path('files/uploaded/', FileUploadedAPIView.as_view(), name='file-uploaded'),
]
