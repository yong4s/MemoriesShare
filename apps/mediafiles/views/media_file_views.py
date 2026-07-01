import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.mediafiles.serializers import MediaFileListQuerySerializer
from apps.mediafiles.serializers import MediaFileUpdateSerializer
from apps.mediafiles.serializers import MediaFileUploadRequestSerializer
from apps.mediafiles.serializers import MediaFileUploadResponseSerializer
from apps.mediafiles.views.base import BaseMediaFileAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


@extend_schema(tags=['MediaFiles'])
class MediaFileListAPIView(BaseMediaFileAPIView):
    """RESTful MediaFiles collection - GET for list, POST for upload URL"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self):
        return get_container().mediafile_service()

    def get(self, request):
        query_serializer = MediaFileListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        event_uuid = query_serializer.validated_data.get('event_uuid')

        if event_uuid:
            files = self.service.get_files_for_event(str(event_uuid), request.user.id)
        else:
            files = self.service.get_user_files(request.user.id)

        return Response({'files': files}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MediaFileUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.service.generate_upload_url(
            user_id=request.user.id,
            event_uuid=str(serializer.validated_data['event_uuid']),
            album_uuid=str(serializer.validated_data['album_uuid']),
            file_name=serializer.validated_data['file_name'],
            content_type=serializer.validated_data['content_type'],
        )

        response_serializer = MediaFileUploadResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['MediaFiles'])
class MediaFileAPIView(BaseMediaFileAPIView):
    """RESTful MediaFile resource - GET/PUT/DELETE for individual files"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self):
        return get_container().mediafile_service()

    def get(self, request, file_uuid):
        if request.query_params.get('download') == 'true':
            result = self.service.generate_download_url(str(file_uuid), request.user.id)
        else:
            result = self.service.get_file_metadata(str(file_uuid), request.user.id)

        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, file_uuid):
        serializer = MediaFileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.service.update_file_metadata(
            file_uuid=str(file_uuid),
            user_id=request.user.id,
            metadata=serializer.validated_data,
        )

        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, file_uuid):
        self.service.delete_file(str(file_uuid), request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
