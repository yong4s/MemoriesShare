import logging
from typing import Dict
from typing import Optional

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.models.custom_user import CustomUser
from apps.events.models.invite_link_event import InviteEventLink
from apps.shared.exceptions.user_exceptions import UserAuthenticationError
from apps.shared.exceptions.user_exceptions import UserCreationError
from apps.shared.exceptions.user_exceptions import UserValidationError

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and JWT token management service"""

    def __init__(self, user_dal: UserDAL = None):
        self.user_dal = user_dal or UserDAL()

    def authenticate_user(self, email: str, password: str) -> dict[str, any]:
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

            # Generate JWT tokens
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
    def register_user(self, email: str, password: str, first_name: str = '', last_name: str = '') -> dict[str, any]:
        """Register new user and return tokens"""
        try:
            # Check if user exists
            if self.user_dal.get_by_email(email, registered_only=True):
                msg = 'User with this email already exists'
                raise UserValidationError(msg)

            # Create user
            user = self.user_dal.create_registered_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Generate tokens
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

    @transaction.atomic
    def authenticate_guest(self, invite_token: str, guest_name: str = '') -> dict[str, any]:
        """Authenticate guest user with invite token"""
        try:
            # Validate invite token (convert string to UUID if needed)
            try:
                if isinstance(invite_token, str) and len(invite_token) == 36:
                    # UUID format from InviteEventLink
                    invite = InviteEventLink.objects.get(invite_token=invite_token)
                else:
                    # Handle string token format
                    invite = InviteEventLink.objects.filter(invite_token=invite_token).first()

                if not invite or not invite.is_active:
                    msg = 'Invalid or expired invitation'
                    raise UserValidationError(msg)

            except InviteEventLink.DoesNotExist:
                msg = 'Invalid invitation token'
                raise UserValidationError(msg)

            # Check if token already used
            existing_user = self.user_dal.get_by_invite_token(str(invite.invite_token))
            if existing_user:
                # Return existing guest user
                refresh = RefreshToken.for_user(existing_user)
                logger.info(f'Guest user login with existing token: {str(invite.invite_token)[:8]}...')

                return {
                    'user': existing_user,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                }

            # Create new guest user
            final_guest_name = guest_name or f'Guest User {invite.event.event_name[:20]}'

            guest_user = self.user_dal.create_guest_user(
                guest_name=final_guest_name, invite_token=str(invite.invite_token)
            )

            # Mark invite as used
            invite.used_count += 1
            invite.save(update_fields=['used_count'])

            # Generate tokens
            refresh = RefreshToken.for_user(guest_user)

            logger.info(f'Created guest user from invite: {final_guest_name}')

            return {
                'user': guest_user,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
            }

        except Exception as e:
            logger.exception(f'Guest authentication error: {e}')
            raise UserAuthenticationError(str(e))

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
            user.save(update_fields=['password'])

            logger.info(f'Password changed for user {user.email}')
            return True

        except Exception as e:
            logger.exception(f'Password change error for user {user.id}: {e}')
            raise UserValidationError(str(e))

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
