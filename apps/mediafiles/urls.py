from django.urls import path

from .views import FileBulkDownloadUrlsAPIView
from .views import FileDeleteAPIView
from .views import FileDownloadUrlAPIView
from .views import FileMetadataAPIView
from .views import FileUploadedAPIView
from .views import FileUploadUrlAPIView
from .views import GalleryUploadUrlAPIView

# urlpatterns = [
#     path('upload/<int:album_pk>/', MediaFileUploadView.as_view(), name='file-upload'),

# ]

urlpatterns = [
    # S3 File Operations
    path(
        "upload/<str:event_gallery_url>/",
        GalleryUploadUrlAPIView.as_view(),
        name="gallery-upload",
    ),
    path("files/upload/", FileUploadUrlAPIView.as_view(), name="file-upload-url"),
    path("files/download/", FileDownloadUrlAPIView.as_view(), name="file-download-url"),
    path(
        "files/bulk-download/",
        FileBulkDownloadUrlsAPIView.as_view(),
        name="file-bulk-download-urls",
    ),
    path("files/delete/", FileDeleteAPIView.as_view(), name="file-delete"),
    path(
        "files/<str:event_uuid>/metadata/",
        FileMetadataAPIView.as_view(),
        name="file-metadata",
    ),
    path("files/uploaded/", FileUploadedAPIView.as_view(), name="file-uploaded"),
]
