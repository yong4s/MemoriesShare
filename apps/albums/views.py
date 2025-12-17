from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.albums.serializers import AlbumCreateSerializer
from apps.albums.serializers import AlbumDetailSerializer
from apps.albums.serializers import AlbumListSerializer
from apps.albums.serializers import MediaFileSerializer
from apps.albums.services import AlbumService
from apps.events.services.event_service import EventService
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.exceptions.exception import S3ServiceError


@extend_schema(tags=['Albums'])
class AlbumCreateApiView(BaseAPIView):
    def post(self, request):
        """Create album for event by UUID from payload"""

        # Get event_uuid from payload
        event_uuid = request.data.get('event_uuid')
        if not event_uuid:
            return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get event through service instead of direct model access
        event_service = EventService()
        try:
            event = event_service.get_event_detail(event_uuid, self.request.user.id)
        except Exception:
            return Response(
                {'error': 'Event not found or access denied'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AlbumCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        album = AlbumService().create_album(serializer, event=event, user_id=self.request.user.id)

        return Response(AlbumDetailSerializer(album).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Albums'])
class AlbumListApiView(BaseAPIView):
    def get(self, request, event_uuid):
        """Get list of albums for event by UUID"""

        # Get event through service instead of direct model access
        event_service = EventService()
        try:
            event = event_service.get_event_detail(event_uuid, self.request.user.id)
        except Exception:
            return Response(
                {'error': 'Event not found or access denied'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get albums through service
        albums = AlbumService().get_albums_for_event(self.request.user.id, event.id)

        return Response(AlbumListSerializer(albums, many=True).data, status=status.HTTP_200_OK)


@extend_schema(tags=['Albums'])
class AlbumDeleteApiView(BaseAPIView):
    def delete(self, request, album_uuid):
        """Delete album by UUID"""

        from apps.albums.models import Album

        album = get_object_or_404(Album, album_uuid=album_uuid)

        if album.event.user_id != self.user_id:
            msg = 'Only event owner can delete albums'
            raise PermissionDenied(msg)

        self.get_service().delete_album_by_uuid(album_uuid, self.user_id)

        return Response({'success': 'Album deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    def get_service(self):
        return AlbumService()
