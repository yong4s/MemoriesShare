import logging

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.exceptions import InvalidUserIdError
from apps.albums.models import Album
from apps.events.models import Event
from apps.shared.auth.permissions import HasJWTAuth
from apps.shared.exceptions.exception import S3ServiceError

from .models import MediaFile
from .serializers import MediaFileSerializer
from .services import MediafileService

logger = logging.getLogger(__name__)


# class MediaFileUploadView(generics.CreateAPIView):
#     serializer_class = MediaFileSerializer
#     queryset = MediaFile.objects.all()
#     services = MediafileService()
#     permission_classes = [HasAPIKey]
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         user = request.user
#         album_id = self.kwargs.get('album_pk')
#
#         media_file = self.services.create_mediafile(serializer, user, album_id)
#
#         if not media_file:
#             return Response({"error": "Failed to create media file"}, status=status.HTTP_400_BAD_REQUEST)
#
#         return Response(self.get_serializer(media_file).data, status=status.HTTP_201_CREATED)


class MediaFileListCreateView(generics.ListCreateAPIView):
    serializer_class = MediaFileSerializer
    permission_classes = [HasJWTAuth]

    def get_queryset(self):
        album_id = self.kwargs['album_pk']
        return MediaFile.objects.filter(album_id=album_id)

    def perform_create(self, serializer):
        album_id = self.kwargs['album_pk']
        serializer.save(album_id=album_id, uploaded_by=self.request.user)


# Retrieve a Single Media File
class MediaFileDetailView(generics.RetrieveAPIView):
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer
    permission_classes = [HasJWTAuth]


# Update a Media File (e.g., modify the URL)
class MediaFileUpdateView(generics.UpdateAPIView):
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer
    permission_classes = [HasJWTAuth]


# Delete a Media File
class MediaFileDeleteView(generics.DestroyAPIView):
    queryset = MediaFile.objects.all()
    permission_classes = [HasJWTAuth]


# ==============================================================================
# BASE MEDIAFILE API VIEW
# ==============================================================================


@method_decorator(csrf_exempt, name='dispatch')
class BaseMediaFileAPIView(APIView):
    """Базовий клас для MediaFile API з централізованою обробкою помилок"""

    permission_classes = [HasJWTAuth]

    def get_service(self):
        """Отримати інстанс сервісу для кожного запиту (stateless)"""
        return MediafileService()

    def get_user_id(self, required=True):
        """
        Отримує та валідує user_id із запиту
        Підтримує як API key (user_id в payload), так і JWT (request.user.id)

        Args:
            required (bool): Чи є user_id обов'язковим

        Returns:
            int: user_id або None якщо не required

        Raises:
            ValidationError: Якщо user_id відсутній або невалідний
        """
        from django.contrib.auth.models import AnonymousUser

        # Для JWT аутентифікації - використовуємо request.user.id
        if (
            hasattr(self.request, 'user')
            and self.request.user
            and not isinstance(self.request.user, AnonymousUser)
            and self.request.user.is_authenticated
        ):
            return self.request.user.id

        # Для API key аутентифікації - шукаємо user_id в payload
        user_id = self.request.data.get('user_id')

        if required and not user_id:
            raise ValidationError('user_id is required in request body')

        if user_id and not isinstance(user_id, int):
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                raise ValidationError('user_id must be a valid integer')

        return user_id

    def handle_exception(self, exc):
        """Централізована обробка помилок для MediaFile операцій"""
        if isinstance(exc, S3ServiceError):
            return Response(
                {'error': 'S3 service error', 'details': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        elif isinstance(exc, PermissionDenied):
            return Response({'error': 'Permission denied', 'details': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, NotFound):
            return Response({'error': 'Not found', 'details': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, ValidationError):
            return Response({'error': 'Validation error', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(exc, InvalidUserIdError):
            return Response({'error': 'Invalid user', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.error(f'Unexpected error: {exc}')
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==============================================================================
# MEDIAFILE FILE OPERATIONS
# ==============================================================================


class GalleryUploadUrlAPIView(BaseMediaFileAPIView):
    """Генерація presigned URL для завантаження в галерею події за gallery_url"""

    def post(self, request, event_uuid):
        """
        Згенерувати presigned URL для завантаження файлу в галерею події

        URL: POST /mediafiles/upload/{event_uuid}/
        Payload: {
            "file_type": "image/jpeg",
            "album_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": 2
        }
        """
        required_fields = ['file_type', 'album_uuid', 'user_id']
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        if missing_fields:
            return Response(
                {'error': f"Missing required fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Отримуємо та валідуємо user_id
            user_id = self.get_user_id()

            # Отримуємо подію за gallery_url
            event = get_object_or_404(Event, event_uuid=event_uuid)

            # Перевіряємо доступ користувача до події (власник або запрошений гість)
            is_owner = event.user_id == user_id
            is_guest = event.guests.filter(user_id=user_id).exists()

            if not (is_owner or is_guest):
                raise PermissionDenied('You do not have permission to upload files to this event')

            # Отримуємо дані з payload
            file_type = request.data.get('file_type')
            album_uuid = request.data.get('album_uuid')

            # Валідуємо album_uuid
            album = get_object_or_404(Album, album_uuid=album_uuid, event=event)

            # Генеруємо UUID для файлу
            import uuid

            file_uuid = str(uuid.uuid4())

            # Формуємо S3 key у форматі: user-bucket-{user_id}/{event_uuid}/{album_uuid}/{file_uuid}
            s3_key = f'user-bucket-{event.user_id}/{event.event_uuid}/{album_uuid}/{file_uuid}'

            # Генеруємо presigned URL
            from apps.shared.storage.s3_utils import S3Service

            s3_service = S3Service()

            presigned_url = s3_service.generate_upload_url(
                key=s3_key,
                content_type=file_type,
                expiration=3600,
                user_id=None,  # Не валідуємо user_id для спрощення
                event_uuid=None,  # Не валідуємо для спрощення
            )

            logger.info(f'Generated gallery upload URL for event {event_uuid}, album {album_uuid}')

            return Response(
                {
                    'upload_url': presigned_url,
                    's3_key': s3_key,
                    'file_uuid': file_uuid,
                    'event_uuid': str(event.event_uuid),
                    'album_uuid': album_uuid,
                    'expires_in': 3600,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            return self.handle_exception(exc)


# ==============================================================================
# FILE OPERATIONS (Moved from Events app)
# ==============================================================================


class FileUploadUrlAPIView(BaseMediaFileAPIView):
    """Генерація URL для завантаження файлів"""

    def post(self, request):
        """Згенерувати URL для завантаження файлу"""
        required_fields = ['event_uuid', 'album_name', 'file_type', 'user_id']
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        if missing_fields:
            return Response(
                {'error': f"Missing required fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event_uuid = request.data.get('event_uuid')
            # Використовуємо MediaFileService для генерації URL (включає перевірку доступу)
            result = self.get_service().generate_upload_url_by_uuid(
                event_uuid=event_uuid,
                user_id=request.data.get('user_id'),
                album_name=request.data.get('album_name'),
                file_type=request.data.get('file_type'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)


class FileDownloadUrlAPIView(BaseMediaFileAPIView):
    """Генерація URL для скачування файлів"""

    def post(self, request):
        """Згенерувати URL для скачування файлу"""
        required_fields = ['event_uuid', 's3_key', 'user_id']
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        if missing_fields:
            return Response(
                {'error': f"Missing required fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event_uuid = request.data.get('event_uuid')
            # Використовуємо MediaFileService для генерації URL (включає перевірку доступу)
            result = self.get_service().generate_download_url_by_uuid(
                event_uuid=event_uuid,
                user_id=request.data.get('user_id'),
                s3_key=request.data.get('s3_key'),
                filename=request.data.get('filename'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)


class FileBulkDownloadUrlsAPIView(BaseMediaFileAPIView):
    """Генерація URL для скачування множини файлів"""

    def post(self, request):
        """Згенерувати URL для скачування множини файлів"""
        event_uuid = request.data.get('event_uuid')
        s3_keys = request.data.get('s3_keys', [])
        user_id = request.data.get('user_id')

        if not all([event_uuid, s3_keys, user_id]):
            return Response(
                {'error': 'event_uuid, s3_keys and user_id are required'}, status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(s3_keys, list) or len(s3_keys) == 0:
            return Response({'error': 's3_keys must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Використовуємо MediaFileService для генерації URL (включає перевірку доступу)
            result = self.get_service().generate_bulk_download_urls_by_uuid(
                event_uuid=event_uuid, user_id=user_id, s3_keys=s3_keys
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)


class FileDeleteAPIView(BaseMediaFileAPIView):
    """Видалення файлу з S3"""

    def delete(self, request):
        """Видалити файл з S3"""
        event_uuid = request.data.get('event_uuid')
        s3_key = request.data.get('s3_key')
        user_id = request.data.get('user_id')

        if not all([event_uuid, s3_key, user_id]):
            return Response(
                {'error': 'event_uuid, s3_key and user_id are required'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Використовуємо MediaFileService для видалення файлу (включає перевірку доступу)
            self.get_service().delete_file_by_uuid(event_uuid=event_uuid, user_id=user_id, s3_key=s3_key)
            return Response({'message': 'File deleted successfully'}, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)


class FileMetadataAPIView(BaseMediaFileAPIView):
    """Отримання метаданих файлу"""

    def get(self, request, event_uuid):
        """Отримати метадані файлу"""
        s3_key = request.query_params.get('s3_key')
        user_id = request.query_params.get('user_id')

        if not all([s3_key, user_id]):
            return Response({'error': 's3_key and user_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Використовуємо MediaFileService для отримання метаданих з перевіркою доступу
            result = self.get_service().get_file_metadata_by_uuid(event_uuid=event_uuid, user_id=user_id, s3_key=s3_key)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)


class FileUploadedAPIView(BaseMediaFileAPIView):
    """Підтвердження успішного завантаження файлу"""

    def post(self, request):
        """Обробити завантажений файл"""
        required_fields = ['event_uuid', 's3_key', 'file_type', 'user_id']
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        if missing_fields:
            return Response(
                {'error': f"Missing required fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event_uuid = request.data.get('event_uuid')
            # Використовуємо MediaFileService для обробки файлу (включає перевірку доступу)
            result = self.get_service().process_uploaded_file_by_uuid(
                event_uuid=event_uuid,
                user_id=request.data.get('user_id'),
                s3_key=request.data.get('s3_key'),
                file_type=request.data.get('file_type'),
                file_uuid=request.data.get('file_uuid'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)
