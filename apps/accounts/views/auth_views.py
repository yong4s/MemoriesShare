import logging

from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import inline_serializer
from rest_framework import status
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.serializers import CustomTokenObtainPairSerializer
from apps.accounts.serializers import LoginMethodsRequestSerializer
from apps.accounts.serializers import LoginMethodsResponseSerializer
from apps.accounts.serializers import PasswordlessRequestSerializer
from apps.accounts.serializers import PasswordlessVerifySerializer
from apps.accounts.serializers import SetPasswordSerializer
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.serializers import UserRegistrationSerializer
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.passwordless_service import PasswordlessService
from apps.accounts.services.user_service import UserService
from apps.shared.utils.general import get_client_ip
from apps.shared.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

PASSWORDLESS_REQUEST_SUCCESS_SERIALIZER = inline_serializer(
    name='PasswordlessRequestSuccessSerializer',
    fields={
        'success': drf_serializers.BooleanField(),
        'message': drf_serializers.CharField(),
        'expires_in_minutes': drf_serializers.IntegerField(),
        'rate_limit_info': drf_serializers.DictField(),
        'note': drf_serializers.CharField(),
    },
)

PASSWORDLESS_VERIFY_SUCCESS_SERIALIZER = inline_serializer(
    name='PasswordlessVerifySuccessSerializer',
    fields={
        'message': drf_serializers.CharField(),
        'access': drf_serializers.CharField(),
        'refresh': drf_serializers.CharField(),
        'user': drf_serializers.DictField(),
    },
)

PASSWORDLESS_ERROR_SERIALIZER = inline_serializer(
    name='PasswordlessErrorSerializer',
    fields={
        'success': drf_serializers.BooleanField(),
        'error': drf_serializers.CharField(),
        'message': drf_serializers.CharField(),
    },
)


class BaseAuthAPIView(APIView):
    """Base view for authentication operations"""

    def __init__(self, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self._auth_service = auth_service

    def get_service(self):
        return self._auth_service or AuthService()

    @staticmethod
    def _get_client_ip(request):
        return get_client_ip(request)

    @staticmethod
    def _get_passwordless_service():
        return PasswordlessService()

    @staticmethod
    def _get_rate_limiter():
        return RateLimiter()

    @staticmethod
    def _rate_limit_response(retry_after_seconds: int) -> Response:
        return Response(
            {
                'success': False,
                'error': 'rate_limit_exceeded',
                'message': f'Too many requests. Try again in {retry_after_seconds} seconds.',
                'retry_after_seconds': retry_after_seconds,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )


@extend_schema(tags=['Authentication'])
class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT token obtain view with additional user data.

    Adds IP and email sliding-window rate limits to limit brute-force
    credential guessing.
    """

    serializer_class = CustomTokenObtainPairSerializer

    LOGIN_EMAIL_LIMIT = 5
    LOGIN_EMAIL_WINDOW_SECONDS = 60
    LOGIN_IP_LIMIT = 20
    LOGIN_IP_WINDOW_SECONDS = 60

    def _get_rate_limiter(self) -> RateLimiter:
        return RateLimiter()

    @staticmethod
    def _client_ip(request) -> str | None:
        return get_client_ip(request)

    def _enforce_rate_limits(self, request) -> Response | None:
        limiter = self._get_rate_limiter()
        ip = self._client_ip(request)
        email = (request.data or {}).get('email', '')
        if ip:
            allowed, info = limiter.check_custom_rate_limit(
                'login_ip', ip, self.LOGIN_IP_LIMIT, self.LOGIN_IP_WINDOW_SECONDS
            )
            if not allowed:
                return self._rate_limited(info)
        if email:
            allowed, info = limiter.check_custom_rate_limit(
                'login_email', email.lower().strip(), self.LOGIN_EMAIL_LIMIT, self.LOGIN_EMAIL_WINDOW_SECONDS
            )
            if not allowed:
                return self._rate_limited(info)
        return None

    @staticmethod
    def _rate_limited(info: dict) -> Response:
        retry_after = int(info.get('retry_after_seconds', 0))
        return Response(
            {
                'success': False,
                'error': 'rate_limit_exceeded',
                'message': f'Too many login attempts. Try again in {retry_after} seconds.',
                'retry_after_seconds': retry_after,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def post(self, request, *args, **kwargs):
        limited = self._enforce_rate_limits(request)
        if limited is not None:
            return limited

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            email = (request.data or {}).get('email', '')
            logger.info(f'User {email} logged in successfully')

        return response


@extend_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    """JWT token refresh view"""


@extend_schema(tags=['Authentication'])
class UserRegistrationView(BaseAuthAPIView):
    """User registration with JWT tokens"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Register new user and return tokens"""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.get_service().register_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
            )

            return Response(
                {
                    'message': 'User created successfully',
                    'user': UserProfileSerializer(result['user']).data,
                    'tokens': result['tokens'],
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class LogoutView(BaseAuthAPIView):
    """Logout user and blacklist refresh token"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Logout user by blacklisting refresh token"""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success = self.get_service().logout_user(refresh_token)

            if success:
                user_email = getattr(request.user, 'email', 'anonymous')
                logger.info('User %s logged out', user_email)
                return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_status(request):
    """Check authentication status"""
    return Response({'authenticated': True, 'user': UserProfileSerializer(request.user).data})


@extend_schema(tags=['System'])
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({'status': 'ok', 'message': 'Authentication API is healthy'})


@extend_schema(tags=['Passwordless Authentication'])
class PasswordlessRequestView(BaseAuthAPIView):
    """Request verification code for passwordless authentication"""

    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordlessRequestSerializer,
        responses={
            202: PASSWORDLESS_REQUEST_SUCCESS_SERIALIZER,
            429: PASSWORDLESS_ERROR_SERIALIZER,
            400: PASSWORDLESS_ERROR_SERIALIZER,
        },
        auth=[],
    )
    def post(self, request):
        """Send verification code to email"""
        serializer = PasswordlessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._get_passwordless_service().request_verification_code(
            email=serializer.validated_data['email'],
            ip_address=self._get_client_ip(request),
        )
        if result.get('success'):
            return Response(result, status=status.HTTP_202_ACCEPTED)
        if result.get('error') == 'rate_limit_exceeded':
            return Response(result, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Passwordless Authentication'])
class PasswordlessVerifyView(BaseAuthAPIView):
    """Verify code and authenticate user"""

    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordlessVerifySerializer,
        responses={
            200: PASSWORDLESS_VERIFY_SUCCESS_SERIALIZER,
            429: PASSWORDLESS_ERROR_SERIALIZER,
            403: PASSWORDLESS_ERROR_SERIALIZER,
            400: PASSWORDLESS_ERROR_SERIALIZER,
        },
        auth=[],
    )
    def post(self, request):
        """Verify code and return JWT tokens"""
        serializer = PasswordlessVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._get_passwordless_service().verify_code_and_authenticate(
            email=serializer.validated_data['email'],
            user_code=serializer.validated_data['code'],
            ip_address=self._get_client_ip(request),
        )
        if result.get('success'):
            logger.info(f"Successful passwordless login for: {serializer.validated_data['email']}")
            return Response(
                {
                    'message': result['message'],
                    'access': result['access'],
                    'refresh': result['refresh'],
                    'user': result['user'],
                },
                status=status.HTTP_200_OK,
            )
        if result.get('error') == 'attempts_exceeded':
            return Response(result, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if result.get('error') == 'account_disabled':
            return Response(result, status=status.HTTP_403_FORBIDDEN)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    deprecated=True,
    description='Deprecated. Use POST /accounts/profile/set-password/ instead.',
)
class SetPasswordView(BaseAuthAPIView):
    """Deprecated alias for setting a password on an authenticated account.

    Retained for one release for backward compatibility. New clients must
    call `POST /accounts/profile/set-password/` on the profile namespace.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserService().set_account_password(
                user=request.user,
                password=serializer.validated_data['password'],
            )
        except Exception as exc:
            logger.exception(f'Legacy set-password failed for user {request.user.id}: {exc}')
            return Response(
                {'error': 'Failed to set password'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(
            {
                'message': 'Password set successfully.',
                'deprecation': 'Use POST /accounts/profile/set-password/ instead.',
            },
            status=status.HTTP_200_OK,
        )
        response['Deprecation'] = 'true'
        return response


LOGIN_METHODS_RATE_LIMIT = 10
LOGIN_METHODS_WINDOW_SECONDS = 60


@extend_schema(tags=['Authentication'])
class LoginMethodsView(BaseAuthAPIView):
    """Discover which sign-in methods are available for an email.

    Anti-enumeration: response shape is identical for known and unknown
    emails. Passwordless is universally advertised (anyone may request
    a code). IP rate limiting adds a further brute-force barrier.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginMethodsRequestSerializer,
        responses={
            200: LoginMethodsResponseSerializer,
            429: PASSWORDLESS_ERROR_SERIALIZER,
            400: PASSWORDLESS_ERROR_SERIALIZER,
        },
        auth=[],
    )
    def post(self, request):
        serializer = LoginMethodsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = self._get_client_ip(request)
        if ip:
            limiter = self._get_rate_limiter()
            allowed, info = limiter.check_custom_rate_limit(
                'login_methods_ip', ip, LOGIN_METHODS_RATE_LIMIT, LOGIN_METHODS_WINDOW_SECONDS
            )
            if not allowed:
                return self._rate_limit_response(int(info.get('retry_after_seconds', 0)))

        result = self.get_service().get_login_methods(serializer.validated_data['email'])
        return Response(result, status=status.HTTP_200_OK)


# Alias for backwards compatibility
AuthStatusView = auth_status
HealthCheckView = health_check
