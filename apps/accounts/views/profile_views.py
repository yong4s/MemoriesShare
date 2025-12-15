import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import CanModifyUserAccount
from apps.accounts.permissions import IsUserOwner
from apps.accounts.serializers import PasswordChangeSerializer
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.user_service import UserService
from apps.shared.base.base_api_view import BaseAPIView

logger = logging.getLogger(__name__)


class BaseUserAPIView(BaseAPIView):
    """Base view for user profile operations"""

    def __init__(self, user_service=None, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self._user_service = user_service
        self._auth_service = auth_service

    def get_service(self):
        return self._user_service or UserService()

    def get_auth_service(self):
        return self._auth_service or AuthService()


@extend_schema(tags=["Authentication"])
class UserProfileView(BaseUserAPIView):
    """User profile management"""

    permission_classes = [IsAuthenticated, IsUserOwner]

    def get(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Update current user profile"""
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )

        if serializer.is_valid():
            try:
                updated_user = self.get_service().update_user_profile(
                    user=request.user, **serializer.validated_data
                )

                logger.info(f"User {request.user.email} updated profile")
                return Response(UserProfileSerializer(updated_user).data)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Authentication"])
class PasswordChangeView(BaseUserAPIView):
    """Change user password"""

    permission_classes = [IsAuthenticated, CanModifyUserAccount]

    def post(self, request):
        """Change current user password"""
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            try:
                success = self.get_auth_service().change_password(
                    user=request.user,
                    old_password=serializer.validated_data["old_password"],
                    new_password=serializer.validated_data["new_password"],
                )

                if success:
                    logger.info(f"User {request.user.email} changed password")
                    return Response(
                        {"message": "Password changed successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Failed to change password"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
