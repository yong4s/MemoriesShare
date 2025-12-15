import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.permissions import IsActiveUser
from apps.accounts.serializers import AnonymousGuestSerializer
from apps.accounts.serializers import CustomTokenObtainPairSerializer
from apps.accounts.serializers import PasswordlessRequestSerializer
from apps.accounts.serializers import PasswordlessVerifySerializer
from apps.accounts.serializers import SetPasswordSerializer
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.serializers import UserRegistrationSerializer
from apps.accounts.services.auth_service import AuthService
from apps.shared.base.base_api_view import BaseAPIView

logger = logging.getLogger(__name__)


class BaseAuthAPIView(BaseAPIView):
    """Base view for authentication operations"""

    def __init__(self, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self._auth_service = auth_service

    def get_service(self):
        return self._auth_service or AuthService()


@extend_schema(tags=["Authentication"])
class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT token obtain view with additional user data"""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.user
                logger.info(f"User {user.email} logged in successfully")

        return response


@extend_schema(tags=["Authentication"])
class CustomTokenRefreshView(TokenRefreshView):
    """JWT token refresh view"""


@extend_schema(tags=["Authentication"])
class UserRegistrationView(BaseAuthAPIView):
    """User registration with JWT tokens"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Register new user and return tokens"""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.get_service().register_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                first_name=serializer.validated_data.get("first_name", ""),
                last_name=serializer.validated_data.get("last_name", ""),
            )

            return Response(
                {
                    "message": "User created successfully",
                    "user": UserProfileSerializer(result["user"]).data,
                    "tokens": result["tokens"],
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Authentication"])
class LogoutView(BaseAuthAPIView):
    """Logout user and blacklist refresh token"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logout user by blacklisting refresh token"""
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success = self.get_service().logout_user(refresh_token)

            if success:
                logger.info(f"User {request.user.email} logged out")
                return Response(
                    {"message": "Logged out successfully"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid refresh token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Authentication"])
class AnonymousGuestLoginView(BaseAuthAPIView):
    """Login as anonymous guest using invite token"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create anonymous guest user and return tokens"""
        serializer = AnonymousGuestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.get_service().authenticate_guest(
                invite_token=serializer.validated_data["invite_token"],
                guest_name=serializer.validated_data.get("guest_name", ""),
            )

            logger.info(f'Anonymous guest authenticated: {result["user"].display_name}')

            return Response(
                {
                    "message": "Anonymous guest authenticated successfully",
                    "user": UserProfileSerializer(result["user"]).data,
                    "tokens": result["tokens"],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_status(request):
    """Check authentication status"""
    return Response(
        {"authenticated": True, "user": UserProfileSerializer(request.user).data}
    )


@extend_schema(tags=["System"])
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({"status": "ok", "message": "Authentication API is healthy"})


@extend_schema(tags=["Passwordless Authentication"])
class PasswordlessRequestView(BaseAuthAPIView):
    """Request verification code for passwordless authentication"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Send verification code to email"""
        serializer = PasswordlessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from apps.accounts.services.passwordless_service import PasswordlessService
            
            service = PasswordlessService()
            result = service.request_verification_code(
                email=serializer.validated_data["email"]
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Passwordless code request failed: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=["Passwordless Authentication"])
class PasswordlessVerifyView(BaseAuthAPIView):
    """Verify code and authenticate user"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Verify code and return JWT tokens"""
        serializer = PasswordlessVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from apps.accounts.services.passwordless_service import PasswordlessService
            
            service = PasswordlessService()
            result = service.verify_code_and_authenticate(
                email=serializer.validated_data["email"],
                user_code=serializer.validated_data["code"]
            )

            logger.info(f"Successful passwordless login for: {serializer.validated_data['email']}")

            return Response(
                {
                    "message": "Authentication successful",
                    "access": result["access"],
                    "refresh": result["refresh"],
                    "user": result["user"],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Passwordless verification failed: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=["Authentication"])
class SetPasswordView(BaseAuthAPIView):
    """Set password for passwordless users"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Convert passwordless user to password-based user"""
        user = request.user

        # Check if user is already registered
        if user.is_registered:
            return Response(
                {"error": "User already has a password set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Set password and convert to registered user
            user.set_password(serializer.validated_data["password"])
            user.is_registered = True
            user.save(update_fields=["password", "is_registered"])

            logger.info(f"Password set for passwordless user: {user.email}")

            return Response(
                {"message": "Password set successfully. You can now login with email and password."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Set password failed for user {user.id}: {e}")
            return Response(
                {"error": "Failed to set password"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Alias for backwards compatibility
AuthStatusView = auth_status
HealthCheckView = health_check
