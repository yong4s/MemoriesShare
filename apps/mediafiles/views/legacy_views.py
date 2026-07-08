import logging
from functools import cached_property

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.mediafiles.serializers import LegacyUploadedConfirmSerializer
from apps.mediafiles.views.base import BaseMediaFileAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


class BaseLegacyMediaFileAPIView(BaseMediaFileAPIView):
    """Base for legacy endpoints. Identity comes from request.user, never the body."""

    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self):
        return get_container().mediafile_service()


@extend_schema(tags=['Media Files'])
class FileUploadedAPIView(BaseLegacyMediaFileAPIView):
    """Confirm successful file upload (legacy endpoint still used by the frontend)."""

    @extend_schema(request=LegacyUploadedConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = LegacyUploadedConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.service.process_uploaded_file_by_uuid(
            event_uuid=str(serializer.validated_data['event_uuid']),
            user_id=request.user.id,
            s3_key=serializer.validated_data['s3_key'],
            file_type=serializer.validated_data['file_type'],
            file_uuid=serializer.validated_data.get('file_uuid'),
            album_uuid=str(serializer.validated_data['album_uuid'])
            if serializer.validated_data.get('album_uuid')
            else None,
            file_name=serializer.validated_data.get('file_name'),
        )

        return Response(result, status=status.HTTP_200_OK)
