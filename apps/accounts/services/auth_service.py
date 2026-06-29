import logging
from typing import Any

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.models.custom_user import CustomUser
from apps.shared.exceptions.user_exceptions import UserAuthenticationError
from apps.shared.exceptions.user_exceptions import UserCreationError
from apps.shared.exceptions.user_exceptions import UserValidationError

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and JWT token management service"""

    def __init__(self, user_dal: UserDAL | None = None):
        self.user_dal = user_dal or UserDAL()

    def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user and return tokens with user data"""
        try:
            user = authenticate(email=email, password=password)
            if not user:
                msg = 'Invalid credentials'
                raise UserAuthenticationError(msg)

            if not user.is_active:
                msg = 'User account is disabled'
                raise UserAuthenticationError(msg)

            if not user.is_registered:
                msg = 'Guest users cannot login with credentials'
                raise UserAuthenticationError(msg)

            refresh = RefreshToken.for_user(user)

            logger.info(f'Successful authentication for user: {email}')

            return {
                'user': user,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
            }

        except Exception as e:
            logger.exception(f'Authentication error for {email}: {e}')
            raise UserAuthenticationError(str(e))

    def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh access token"""
        try:
            refresh = RefreshToken(refresh_token)
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        except Exception as e:
            logger.exception(f'Token refresh error: {e}')
            msg = 'Invalid refresh token'
            raise UserAuthenticationError(msg)

    def logout_user(self, refresh_token: str) -> bool:
        """Logout user by blacklisting refresh token"""
        try:
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()
            logger.info('User logged out successfully')
            return True
        except Exception as e:
            logger.exception(f'Logout error: {e}')
            return False

    @transaction.atomic
    def register_user(self, email: str, password: str, first_name: str = '', last_name: str = '') -> dict[str, Any]:
        """Register new user and return tokens"""
        try:
            if self.user_dal.get_by_email(email, registered_only=True):
                msg = 'User with this email already exists'
                raise UserValidationError(msg)

            user = self.user_dal.create_registered_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            refresh = RefreshToken.for_user(user)

            logger.info(f'Registered new user: {email}')

            return {
                'user': user,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
            }

        except Exception as e:
            logger.exception(f'Registration error: {e}')
            raise UserCreationError(str(e))

    def change_password(self, user: CustomUser, old_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            if not user.is_registered:
                msg = 'Only registered users can change passwords'
                raise UserValidationError(msg)

            if not user.check_password(old_password):
                msg = 'Current password is incorrect'
                raise UserValidationError(msg)

            user.set_password(new_password)
            user.password_changed_at = timezone.now()
            user.save(update_fields=['password', 'password_changed_at'])

            logger.info(f'Password changed for user {user.email}')
            return True

        except Exception as e:
            logger.exception(f'Password change error for user {user.id}: {e}')
            raise UserValidationError(str(e))

    def get_login_methods(self, email: str) -> dict[str, Any]:
        """Return available sign-in methods for an email.

        Always returns an identical response shape for known and unknown
        emails to avoid enumeration. Passwordless is universally available
        (any valid email may request a code); password is only true for
        users who have actually set one.
        """
        normalized = (email or '').lower().strip()
        info = self.user_dal.get_login_capabilities(normalized)
        if info is None:
            return {
                'password': False,
                'passwordless': True,
                'preferred': CustomUser.LoginMethod.PASSWORDLESS,
            }
        return {
            'password': bool(info['has_password']),
            'passwordless': True,
            'preferred': info['preferred'],
        }

    def get_user_from_token(self, token: str) -> CustomUser | None:
        """Get user from JWT token"""
        try:
            refresh = RefreshToken(token)
            user_id = refresh.get('user_id')
            if user_id:
                return self.user_dal.get_by_id(user_id)
            return None
        except Exception as e:
            logger.exception(f'Token validation error: {e}')
            return None
