from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.events.services.event_service import EventService
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.exceptions.exception import S3ServiceError

from .serializers import AlbumCreateSerializer, AlbumDetailSerializer, AlbumListSerializer, MediaFileSerializer
from .services import AlbumService


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
            return Response({'error': 'Event not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AlbumCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        album = AlbumService().create_album(serializer, event=event, user_id=self.request.user.id)

        return Response(AlbumDetailSerializer(album).data, status=status.HTTP_201_CREATED)


class AlbumListApiView(BaseAPIView):
    def get(self, request, event_uuid):
        """Get list of albums for event by UUID"""
        
        # Get event through service instead of direct model access
        event_service = EventService()
        try:
            event = event_service.get_event_detail(event_uuid, self.request.user.id)
        except Exception:
            return Response({'error': 'Event not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

        # Get albums through service
        albums = AlbumService().get_albums_for_event(self.request.user.id, event.id)

        return Response(AlbumListSerializer(albums, many=True).data, status=status.HTTP_200_OK)


class AlbumDeleteApiView(BaseAPIView):
    def delete(self, request, album_uuid):
        """Видалити альбом за UUID"""
        from django.shortcuts import get_object_or_404
        from rest_framework.exceptions import PermissionDenied

        from .models import Album

        # Отримуємо альбом за UUID
        album = get_object_or_404(Album, album_uuid=album_uuid)

        # Перевіряємо чи користувач є власником події
        if album.event.user_id != self.user_id:
            raise PermissionDenied('Only event owner can delete albums')

        self.get_service().delete_album_by_uuid(album_uuid, self.user_id)

        return Response({'success': 'Album deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    def get_service(self):
        return AlbumService()
