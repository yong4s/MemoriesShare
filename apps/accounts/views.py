"""
Authentication views using JWT
"""

import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.signals import user_logged_out
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiResponse
from rest_framework import permissions
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from .models import CustomUser
from .serializers import AnonymousGuestSerializer
from .serializers import CustomTokenObtainPairSerializer
from .serializers import PasswordChangeSerializer
from .serializers import UserLoginSerializer
from .serializers import UserProfileSerializer
from .serializers import UserRegistrationSerializer

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user data
    """

    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary='Obtain JWT tokens',
        description='Authenticate user and return access/refresh token pair with user data',
        responses={
            200: OpenApiResponse(description='Successful authentication'),
            401: OpenApiResponse(description='Invalid credentials'),
        },
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Log successful login
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.user
                user_logged_in.send(sender=user.__class__, request=request, user=user)
                logger.info(f'User {user.email} logged in successfully')

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT token refresh view
    """

    @extend_schema(
        summary='Refresh JWT token',
        description='Obtain new access token using refresh token',
        responses={
            200: OpenApiResponse(description='Token refreshed successfully'),
            401: OpenApiResponse(description='Invalid refresh token'),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserRegistrationView(APIView):
    """
    User registration view
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='Register new user',
        description='Create new user account and return JWT tokens',
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description='User created successfully'),
            400: OpenApiResponse(description='Invalid data'),
        },
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens for the new user
            refresh = RefreshToken.for_user(user)

            # Log successful registration
            logger.info(f'New user registered: {user.email}')

            return Response(
                {
                    'message': 'User created successfully',
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    User profile view
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Get user profile',
        description='Get current user profile data',
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary='Update user profile',
        description='Update current user profile data',
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description='Invalid data'),
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            logger.info(f'User {request.user.email} updated profile')
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    Password change view
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Change password',
        description='Change current user password',
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Invalid data'),
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            logger.info(f'User {user.email} changed password')

            return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout view that blacklists refresh token
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Logout user',
        description='Logout user and blacklist refresh token',
        responses={
            200: OpenApiResponse(description='Logged out successfully'),
            400: OpenApiResponse(description='Invalid refresh token'),
            401: OpenApiResponse(description='Authentication required'),
        },
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Send logout signal
            user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)

            logger.info(f'User {request.user.email} logged out')

            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

        except TokenError:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_400_BAD_REQUEST)


class AnonymousGuestLoginView(APIView):
    """
    Login view for anonymous guests using invite tokens
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='Login as anonymous guest',
        description='Create anonymous guest user and return JWT tokens using invite token',
        request=AnonymousGuestSerializer,
        responses={
            200: OpenApiResponse(description='Anonymous guest created and authenticated'),
            400: OpenApiResponse(description='Invalid invite token'),
        },
    )
    def post(self, request):
        serializer = AnonymousGuestSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens for the anonymous guest
            refresh = RefreshToken.for_user(user)

            logger.info(f'Anonymous guest created: {user.display_name} ({user.email})')

            return Response(
                {
                    'message': 'Anonymous guest authenticated successfully',
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary='Check authentication status',
    description='Check if user is authenticated and return user data',
    responses={
        200: OpenApiResponse(description='Authentication status'),
    },
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def auth_status(request):
    """
    Check authentication status
    """
    return Response({'authenticated': True, 'user': UserProfileSerializer(request.user).data})


@extend_schema(
    summary='Check health',
    description='Health check endpoint',
    responses={
        200: OpenApiResponse(description='API is healthy'),
    },
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Health check endpoint
    """
    return Response({'status': 'ok', 'message': 'Authentication API is healthy'})


# Legacy session-based authentication views (for backward compatibility)
@method_decorator(csrf_exempt, name='dispatch')
class SessionLoginView(APIView):
    """
    Session-based login view (legacy support)
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)

            return Response({'message': 'Logged in successfully', 'user': UserProfileSerializer(user).data})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class SessionLogoutView(APIView):
    """
    Session-based logout view (legacy support)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully'})  # apps/accounts/views/guest_views.py


import logging

from django.shortcuts import get_object_or_404

from apps.events.models import Event
from apps.events.services import EventService
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.exceptions.exception import S3ServiceError

from .exceptions import InvalidUserIdError

logger = logging.getLogger(__name__)


class GuestListAPIView(BaseAPIView):
    """Список гостей події"""

    def get_service(self):
        """Return EventService instance"""
        return EventService()

    def get(self, request, event_uuid):
        """Отримати список гостей події за UUID"""
        try:
            user_id = self.user_id

            # Отримуємо подію та гостей через сервіс з перевіркою доступу
            event = self.get_service().get_event_details_by_uuid(event_uuid, user_id)
            guests = self.get_service().get_guests_for_event(event.id, user_id)
            serializer = GuestListSerializer(guests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)

    def post(self, request):
        """Додати гостя до події"""
        try:
            user_id = self.user_id

            # Отримуємо event_uuid з payload
            event_uuid = request.data.get('event_uuid')
            if not event_uuid:
                return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Отримуємо подію через сервіс з перевіркою доступу
            event = self.get_service().get_event_details_by_uuid(event_uuid, user_id)

            serializer = GuestCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Використовуємо сервіс для створення гостя (включає всі перевірки та кешування)
            guest = self.get_service().create_guest(event.id, user_id, serializer.validated_data)

            logger.info(f'Guest {guest.id} added to event {event.event_uuid}')
            return Response(GuestDetailSerializer(guest).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return self.handle_exception(exc)


class GuestDetailAPIView(BaseAPIView):
    """Деталі окремого гостя"""

    def get_service(self):
        """Return EventService instance"""
        return EventService()

    def get(self, request, event_uuid, guest_id):
        """Отримати деталі гостя"""
        try:
            user_id = self.user_id

            # Отримуємо подію через сервіс з перевіркою доступу
            event = self.get_service().get_event_details_by_uuid(event_uuid, user_id)

            # Отримуємо гостя через сервіс
            guest = self.get_service().get_guest(event.id, guest_id, user_id)
            serializer = GuestDetailSerializer(guest)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)

    def put(self, request, guest_id):
        """Оновити гостя за UUID події"""
        try:
            user_id = self.user_id

            # Отримуємо event_uuid з payload
            event_uuid = request.data.get('event_uuid')
            if not event_uuid:
                return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Валідуємо дані
            serializer = GuestDetailSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Використовуємо сервіс для оновлення гостя (вся бізнес-логіка тут)
            updated_guest = self.get_service().update_guest_by_uuid(
                event_uuid, guest_id, user_id, serializer.validated_data
            )

            logger.info(f'Guest {guest_id} updated in event {event_uuid}')
            return Response(GuestDetailSerializer(updated_guest).data, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_exception(exc)

    def delete(self, request, guest_id):
        """Видалити гостя за UUID події"""
        try:
            user_id = self.user_id

            # Отримуємо event_uuid з payload
            event_uuid = request.data.get('event_uuid')
            if not event_uuid:
                return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Використовуємо сервіс для видалення гостя (вся бізнес-логіка тут)
            success = self.get_service().delete_guest_by_uuid(event_uuid, guest_id, user_id)

            if success:
                logger.info(f'Guest {guest_id} deleted from event {event_uuid}')
                return Response({'message': 'Guest deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Failed to delete guest'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            return self.handle_exception(exc)


class GuestUpdateStatusAPIView(BaseAPIView):
    """Швидке оновлення статусу гостя"""

    def get_service(self):
        """Return EventService instance"""
        return EventService()

    def patch(self, request, guest_id):
        """Оновити статус гостя"""
        try:
            user_id = self.user_id

            # Отримуємо event_uuid з payload
            event_uuid = request.data.get('event_uuid')
            if not event_uuid:
                return Response({'error': 'event_uuid is required'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = GuestStatusUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Використовуємо сервіс для оновлення статусу (вся бізнес-логіка тут)
            guest = self.get_service().update_guest_status_by_uuid(
                event_uuid, guest_id, user_id, serializer.validated_data['rsvp_status']
            )

            logger.info(f'Guest {guest_id} status updated to {guest.rsvp_status} in event {event_uuid}')
            return Response(
                {'message': 'Guest status updated', 'rsvp_status': guest.rsvp_status}, status=status.HTTP_200_OK
            )
        except Exception as exc:
            return self.handle_exception(exc)
