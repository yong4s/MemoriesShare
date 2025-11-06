"""
JWT Authentication Views - Login, Register, Refresh, Logout
"""

import logging

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..auth.jwt_service import JWTService
from ..auth.permissions import HasJWTAuth

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(APIView):
    """
    User registration with JWT token response
    POST /auth/register/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Register new user and return JWT tokens"""
        try:
            email = request.data.get('email', '').lower().strip()
            password = request.data.get('password', '')

            # Validate input
            if not email or not password:
                return Response(
                    {'success': False, 'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                return Response(
                    {'success': False, 'error': 'User with this email already exists'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate password
            try:
                validate_password(password)
            except DjangoValidationError as e:
                return Response(
                    {'success': False, 'error': 'Invalid password', 'details': list(e.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create user and tokens
            with transaction.atomic():
                user = User.objects.create_user(email=email, password=password)
                user.is_active = True
                user.save()

                jwt_service = JWTService()
                device_info = request.META.get('HTTP_USER_AGENT', '')
                ip_address = self.get_client_ip(request)

                tokens = jwt_service.create_token_pair(user=user, device_info=device_info, ip_address=ip_address)

            logger.info(f'User registered: {email}')
            return Response(
                {
                    'success': True,
                    'message': 'User registered successfully',
                    'user': {'id': user.id, 'email': user.email, 'is_active': user.is_active},
                    'tokens': tokens,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            logger.warning(f'Validation error during registration: {e}')
            return Response(
                {'success': False, 'error': 'Invalid input data'}, status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.warning(f'User already exists: {e}')
            return Response(
                {'success': False, 'error': 'User with this email already exists'}, status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            logger.exception('Unexpected error during registration')
            return Response(
                {'success': False, 'error': 'Registration failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LoginView(APIView):
    """
    User login with JWT token response
    POST /auth/login/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Login user and return JWT tokens"""
        try:
            email = request.data.get('email', '').lower().strip()
            password = request.data.get('password', '')

            if not email or not password:
                return Response(
                    {'success': False, 'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST
                )

            # Authenticate user
            user = authenticate(request, username=email, password=password)
            if not user:
                return Response(
                    {'success': False, 'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active:
                return Response({'success': False, 'error': 'Account is inactive'}, status=status.HTTP_401_UNAUTHORIZED)

            # Create JWT tokens
            jwt_service = JWTService()
            device_info = request.META.get('HTTP_USER_AGENT', '')
            ip_address = self.get_client_ip(request)

            tokens = jwt_service.create_token_pair(user=user, device_info=device_info, ip_address=ip_address)

            logger.info(f'User logged in: {email}')
            return Response(
                {
                    'success': True,
                    'message': 'Login successful',
                    'user': {'id': user.id, 'email': user.email, 'is_active': user.is_active},
                    'tokens': tokens,
                }
            )

        except AttributeError as e:
            logger.error(f'User attribute error during login: {e}')
            return Response({'success': False, 'error': 'Invalid user data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Unexpected error during login')
            return Response({'success': False, 'error': 'Login failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RefreshTokenView(APIView):
    """
    Refresh access token using refresh token
    POST /auth/refresh/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Refresh access token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {'success': False, 'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST
                )

            jwt_service = JWTService()
            new_tokens = jwt_service.refresh_access_token(refresh_token)

            if not new_tokens:
                return Response(
                    {'success': False, 'error': 'Invalid or expired refresh token'}, status=status.HTTP_401_UNAUTHORIZED
                )

            return Response({'success': True, 'tokens': new_tokens})

        except (AttributeError, ValueError) as e:
            logger.error(f'Token attribute error: {e!s}')
            return Response(
                {'success': False, 'error': 'Invalid token data'}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception('Unexpected error during token refresh')
            return Response(
                {'success': False, 'error': 'Token refresh failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """
    Logout user and invalidate tokens
    POST /auth/logout/
    """

    permission_classes = [HasJWTAuth]

    def post(self, request):
        """Logout user"""
        try:
            # Get refresh token from request
            refresh_token = request.data.get('refresh_token')
            session_id = request.data.get('session_id')  # Optional: logout specific session

            jwt_service = JWTService()

            # Blacklist current access token
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]
                jwt_service.blacklist_token(access_token, 'logout')

            # Blacklist refresh token if provided
            if refresh_token:
                jwt_service.blacklist_token(refresh_token, 'logout')

            # Logout user sessions
            jwt_service.logout_user(request.user, session_id)

            logger.info(f'User logged out: {request.user.email}')
            return Response({'success': True, 'message': 'Logout successful'})

        except AttributeError as e:
            logger.error(f'User attribute error during logout: {e!s}')
            return Response({'success': False, 'error': 'Invalid user data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Unexpected error during logout')
            return Response({'success': False, 'error': 'Logout failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileView(APIView):
    """
    Get current user profile
    GET /auth/profile/
    """

    permission_classes = [HasJWTAuth]

    def get(self, request):
        """Get user profile"""
        try:
            user = request.user
            jwt_service = JWTService()

            # Get user sessions
            sessions = jwt_service.get_user_sessions(user)
            sessions_data = [
                {
                    'id': session.id,
                    'device_info': session.device_info,
                    'ip_address': session.ip_address,
                    'last_activity': session.last_activity,
                    'created_at': session.created_at,
                }
                for session in sessions
            ]

            return Response(
                {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'is_active': user.is_active,
                        'date_joined': user.date_joined,
                        'last_login': user.last_login,
                    },
                    'sessions': sessions_data,
                    'jwt_data': getattr(request, 'jwt_data', {}),
                }
            )

        except AttributeError as e:
            logger.error(f'User attribute error getting profile: {e!s}')
            return Response(
                {'success': False, 'error': 'Invalid user data'}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception('Unexpected error getting profile')
            return Response(
                {'success': False, 'error': 'Failed to get profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutAllSessionsView(APIView):
    """
    Logout from all sessions
    POST /auth/logout-all/
    """

    permission_classes = [HasJWTAuth]

    def post(self, request):
        """Logout from all sessions"""
        try:
            jwt_service = JWTService()

            # Blacklist current access token
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]
                jwt_service.blacklist_token(access_token, 'logout_all')

            # Logout all user sessions
            jwt_service.logout_user(request.user)

            logger.info(f'User logged out from all sessions: {request.user.email}')
            return Response({'success': True, 'message': 'Logged out from all sessions'})

        except AttributeError as e:
            logger.error(f'User attribute error during logout all: {e!s}')
            return Response({'success': False, 'error': 'Invalid user data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Unexpected error during logout all')
            return Response({'success': False, 'error': 'Logout failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateTokenView(APIView):
    """
    Validate JWT token
    POST /auth/validate/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Validate JWT token"""
        try:
            token = request.data.get('token')
            token_type = request.data.get('token_type', 'access')

            if not token:
                return Response({'success': False, 'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

            jwt_service = JWTService()
            payload = jwt_service.verify_token(token, token_type)

            if payload:
                return Response({'success': True, 'valid': True, 'payload': payload})
            else:
                return Response({'success': True, 'valid': False, 'error': 'Invalid or expired token'})

        except (ValueError, KeyError) as e:
            logger.error(f'Token format error: {e!s}')
            return Response(
                {'success': False, 'error': 'Invalid token format'}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception('Unexpected error during token validation')
            return Response(
                {'success': False, 'error': 'Validation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
