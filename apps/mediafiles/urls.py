from django.urls import path

from apps.mediafiles.views import (
    FileUploadedAPIView,
    MediaFileAPIView,
    MediaFileListAPIView,
)

urlpatterns = [
    # RESTful MediaFiles API
    path('', MediaFileListAPIView.as_view(), name='mediafile-list'),  # GET/POST /mediafiles/
    path('<uuid:file_uuid>/', MediaFileAPIView.as_view(), name='mediafile-detail'),  # GET/PUT/DELETE /mediafiles/{uuid}/
    # Upload confirmation (still used by the frontend after a presigned PUT)
    path('files/uploaded/', FileUploadedAPIView.as_view(), name='file-uploaded'),
]
