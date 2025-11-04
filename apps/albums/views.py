from rest_framework import status
from rest_framework.response import Response

from apps.mediafiles.models import MediaFile
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.exceptions.exception import S3ServiceError

from .serializers import AlbumCreateSerializer
from .serializers import AlbumDetailSerializer
from .serializers import AlbumListSerializer
from .serializers import MediaFileSerializer
from .services import AlbumService


class AlbumCreateApiView(BaseAPIView):
    def post(self, request):
        """Створити альбом в події за UUID з payload"""

        # Отримуємо event_uuid з payload
        event_uuid = request.data.get('event_uuid')
        if not event_uuid:
            return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Отримуємо подію за UUID
        event = get_object_or_404(Event, event_uuid=event_uuid)

        # Перевіряємо чи користувач є власником події
        if event.user_id != self.user_id:
            raise PermissionDenied('Only event owner can create albums')

        serializer = AlbumCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        album = self.get_service().create_album(serializer, event=event, user_id=self.user_id)

        return Response(AlbumDetailSerializer(album).data, status=status.HTTP_201_CREATED)

    def get_service(self):
        return AlbumService()


class AlbumListApiView(BaseAPIView):
    def get(self, request, event_uuid):
        """Отримати список альбомів події за UUID"""
        from django.shortcuts import get_object_or_404
        from rest_framework.exceptions import PermissionDenied

        from apps.events.models import Event

        # Отримуємо подію за UUID
        event = get_object_or_404(Event, event_uuid=event_uuid)

        # Перевіряємо доступ через сервісний шар
        from apps.events.services.event_service import EventService

        event_service = EventService()

        has_access = (
            event.user_id == self.user_id  # власник
            or event_service.is_user_guest(event.id, self.user_id)  # гість
            or event.is_public  # публічна подія
        )

        if not has_access:
            raise PermissionDenied("You don't have access to this event's albums")

        # Отримуємо альбоми події
        albums = event.albums.all().order_by('sort_order', 'name')

        return Response(AlbumListSerializer(albums, many=True).data, status=status.HTTP_200_OK)

    def get_service(self):
        return AlbumService()


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
