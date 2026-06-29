import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.albums.serializers import AlbumCreateSerializer
from apps.albums.serializers import AlbumDetailSerializer
from apps.albums.serializers import AlbumListSerializer
from apps.albums.serializers import AlbumUpdateSerializer
from apps.albums.views.base import BaseAlbumAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


@extend_schema(tags=['Albums'])
class AlbumListApiView(BaseAlbumAPIView):
    """RESTful Albums collection - GET for list, POST for create"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def album_service(self):
        return get_container().album_service()

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request, event_uuid):
        event = self.event_service.get_event_detail(event_uuid, request.user.id)
        albums = self.album_service.get_albums_for_event(event, request.user.id)
        return Response(AlbumListSerializer(albums, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, event_uuid):
        event = self.event_service.get_event_detail(event_uuid, request.user.id)

        serializer = AlbumCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        album = self.album_service.create_album(
            event=event,
            user_id=request.user.id,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_public=serializer.validated_data.get('is_public', False),
        )

        return Response(AlbumDetailSerializer(album).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Albums'])
class AlbumAPIView(BaseAlbumAPIView):
    """RESTful Album resource - GET/PUT/DELETE for individual albums"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self):
        return get_container().album_service()

    def get(self, request, album_uuid):
        album = self.service.get_album_detail(album_uuid, request.user.id)
        serializer = AlbumDetailSerializer(album)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, album_uuid):
        serializer = AlbumUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        album = self.service.update_album(album_uuid, serializer.validated_data, request.user.id)
        response_serializer = AlbumDetailSerializer(album)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, album_uuid):
        self.service.delete_album(album_uuid, request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
