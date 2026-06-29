import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.permissions import CanModifyUserAccount
from apps.accounts.permissions import IsUserOwner
from apps.accounts.serializers import PasswordChangeSerializer
from apps.accounts.serializers import SetPasswordSerializer
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.user_service import UserService
from apps.shared.exceptions.user_exceptions import UserValidationError

logger = logging.getLogger(__name__)


class BaseUserAPIView(APIView):
    """Base view for user profile operations"""

    def __init__(self, user_service=None, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self._user_service = user_service
        self._auth_service = auth_service

    def get_service(self):
        return self._user_service or UserService()

    def get_auth_service(self):
        return self._auth_service or AuthService()


@extend_schema(tags=['Authentication'])
class UserProfileView(BaseUserAPIView):
    """User profile management"""

    permission_classes = [IsAuthenticated, IsUserOwner]

    def get(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Update current user profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                updated_user = self.get_service().update_user_profile(user=request.user, **serializer.validated_data)

                logger.info(f'User {request.user.email} updated profile')
                return Response(UserProfileSerializer(updated_user).data)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Profile'])
class AccountPasswordView(BaseUserAPIView):
    """Set or replace the authenticated user's password.

    Primary entry point for users who signed up via passwordless flow and
    now wish to add a password, as well as for users who want to reset
    their password without knowing the old one (use PasswordChangeView
    when the old password is known).

    On success, rotates JWT tokens — old refresh tokens issued before the
    password change remain valid only until their natural expiry, but the
    caller is given a fresh pair. If the client supplies the current
    refresh token in the request body, it is blacklisted.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=SetPasswordSerializer)
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.get_service().set_account_password(
                user=request.user,
                password=serializer.validated_data['password'],
            )
        except UserValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('set_account_password failed for user %s', request.user.id)
            return Response(
                {'error': 'Failed to set password'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        presented_refresh = (request.data or {}).get('refresh')
        if presented_refresh:
            try:
                RefreshToken(presented_refresh).blacklist()
            except TokenError:
                logger.info('Ignored invalid refresh token during password set')

        refresh = RefreshToken.for_user(user)
        logger.info('Password set via profile for user %s', user.email)
        return Response(
            {
                'message': 'Password set successfully.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Authentication'])
class PasswordChangeView(BaseUserAPIView):
    """Change user password"""

    permission_classes = [IsAuthenticated, CanModifyUserAccount]

    def post(self, request):
        """Change current user password"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            try:
                success = self.get_auth_service().change_password(
                    user=request.user,
                    old_password=serializer.validated_data['old_password'],
                    new_password=serializer.validated_data['new_password'],
                )

                if success:
                    logger.info(f'User {request.user.email} changed password')
                    return Response(
                        {'message': 'Password changed successfully'},
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {'error': 'Failed to change password'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
