from django.http import JsonResponse
from rest_framework import status

from apps.accounts.exceptions import InvalidUserUUIdError
from apps.events.exceptions import EventCreationError
from apps.events.exceptions import EventNotFoundError
from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import ParticipantError
from apps.shared.exceptions.exception import S3BucketNotFoundError
from apps.shared.exceptions.exception import S3BucketPermissionError
from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.exceptions.exception import S3UploadException
from apps.shared.exceptions.exception import UserNotFoundError


class S3ExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Handle specific exceptions that should not use DRF's default handling"""

        # S3 Service Exceptions
        if isinstance(exception, S3ServiceError):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        if isinstance(
            exception,
            S3UploadException | S3BucketNotFoundError | S3BucketPermissionError,
        ):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_503_SERVICE_UNAVAILABLE),
            )

        # Event Business Logic Exceptions
        if isinstance(exception, EventCreationError):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_400_BAD_REQUEST),
            )
        if isinstance(exception, EventNotFoundError):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_404_NOT_FOUND),
            )
        if isinstance(exception, EventPermissionError):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_403_FORBIDDEN),
            )
        if isinstance(exception, ParticipantError):
            return JsonResponse(
                {'error': str(exception)},
                status=getattr(exception, 'status_code', status.HTTP_400_BAD_REQUEST),
            )

        # User Related Exceptions
        if isinstance(exception, UserNotFoundError):
            return JsonResponse(
                {'error': 'User not found.'},
                status=getattr(exception, 'status_code', status.HTTP_404_NOT_FOUND),
            )
        if isinstance(exception, InvalidUserUUIdError):
            return JsonResponse(
                {'error': 'Invalid user identifier.'},
                status=getattr(exception, 'status_code', status.HTTP_400_BAD_REQUEST),
            )

        # Let Django/DRF handle other exceptions
        return None
