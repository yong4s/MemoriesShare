"""
Advanced JWT Service with refresh tokens, blacklisting, and session management
"""

import logging
import uuid
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from ..base.models import BlacklistedToken
from ..base.models import UserSession

logger = logging.getLogger(__name__)
User = get_user_model()

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, 'SIMPLE_JWT_SECRET_KEY', 'dev-jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Token expiration times
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)  # Short-lived access tokens
REFRESH_TOKEN_LIFETIME = timedelta(days=7)  # Long-lived refresh tokens
VERIFY_EMAIL_TOKEN_LIFETIME = timedelta(hours=24)  # Email verification tokens


class JWTAuthenticationError(Exception):
    """Custom exception for JWT authentication errors"""


class JWTService:
    """
    Advanced JWT service with refresh tokens, blacklisting, and session management
    """

    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM

    def generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return str(uuid.uuid4())

    def create_access_token(self, user: User, jti: str = None) -> str:
        """
        Create access token for user

        Args:
            user: Django User instance
            jti: Optional JWT ID (will generate if not provided)

        Returns:
            JWT access token string
        """
        if not jti:
            jti = self.generate_jti()

        now = timezone.now()
        payload = {
            'user_id': user.id,
            'email': user.email,
            'token_type': 'access',
            'jti': jti,
            'iat': now.timestamp(),
            'exp': (now + ACCESS_TOKEN_LIFETIME).timestamp(),
            'iss': 'media-flow-api',
            'sub': str(user.id),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f'Created access token for user {user.id} (jti: {jti})')
        return token

    def create_refresh_token(
        self, user: User, device_info: str = '', ip_address: str = None
    ) -> tuple[str, UserSession]:
        """
        Create refresh token and session for user

        Args:
            user: Django User instance
            device_info: Device/browser information
            ip_address: User's IP address

        Returns:
            Tuple of (refresh_token, user_session)
        """
        jti = self.generate_jti()
        now = timezone.now()
        expires_at = now + REFRESH_TOKEN_LIFETIME

        payload = {
            'user_id': user.id,
            'email': user.email,
            'token_type': 'refresh',
            'jti': jti,
            'iat': now.timestamp(),
            'exp': expires_at.timestamp(),
            'iss': 'media-flow-api',
            'sub': str(user.id),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Create user session
        session = UserSession.objects.create(
            user=user, refresh_token_jti=jti, device_info=device_info, ip_address=ip_address, expires_at=expires_at
        )

        logger.info(f'Created refresh token for user {user.id} (jti: {jti})')
        return token, session

    def create_token_pair(self, user: User, device_info: str = '', ip_address: str = None) -> dict[str, Any]:
        """
        Create access and refresh token pair

        Args:
            user: Django User instance
            device_info: Device/browser information
            ip_address: User's IP address

        Returns:
            Dict with access_token, refresh_token, expires_in, token_type
        """
        access_token = self.create_access_token(user)
        refresh_token, session = self.create_refresh_token(user, device_info, ip_address)

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(ACCESS_TOKEN_LIFETIME.total_seconds()),
            'refresh_expires_in': int(REFRESH_TOKEN_LIFETIME.total_seconds()),
            'session_id': session.id,
        }

    def verify_token(self, token: str, token_type: str = 'access') -> dict[str, Any] | None:
        """
        Verify JWT token and return payload

        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')

        Returns:
            Decoded payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get('token_type') != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('token_type')}")
                return None

            # Check if token is blacklisted
            jti = payload.get('jti')
            if jti and BlacklistedToken.is_blacklisted(jti):
                logger.warning(f'Token {jti} is blacklisted')
                return None

            # For refresh tokens, check if session is still active
            if token_type == 'refresh':
                try:
                    session = UserSession.objects.get(refresh_token_jti=jti, is_active=True)
                    session.last_activity = timezone.now()
                    session.save()
                except UserSession.DoesNotExist:
                    logger.warning(f'Refresh token session {jti} not found or inactive')
                    return None

            logger.debug(f"Successfully verified {token_type} token for user: {payload.get('user_id')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning(f'{token_type.title()} token has expired')
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f'Invalid {token_type} token: {e!s}')
            return None
        except (AttributeError, KeyError) as e:
            logger.error(f'Token payload error for {token_type} token: {e!s}')
            return None
        except Exception as e:
            logger.exception(f'Unexpected error verifying {token_type} token')
            return None

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any] | None:
        """
        Create new access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access token or None if invalid
        """
        payload = self.verify_token(refresh_token, 'refresh')
        if not payload:
            return None

        try:
            user = User.objects.get(id=payload['user_id'])
            new_access_token = self.create_access_token(user)

            return {
                'access_token': new_access_token,
                'token_type': 'Bearer',
                'expires_in': int(ACCESS_TOKEN_LIFETIME.total_seconds()),
            }
        except User.DoesNotExist:
            logger.warning(f"User {payload['user_id']} not found for token refresh")
            return None

    def blacklist_token(self, token: str, reason: str = 'logout') -> bool:
        """
        Blacklist a token

        Args:
            token: JWT token to blacklist
            reason: Reason for blacklisting

        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            # Decode without verification to get payload
            payload = jwt.decode(token, options={'verify_signature': False})
            jti = payload.get('jti')
            user_id = payload.get('user_id')
            token_type = payload.get('token_type', 'access')
            exp = payload.get('exp')

            if not jti or not user_id or not exp:
                logger.warning('Token missing required fields for blacklisting')
                return False

            user = User.objects.get(id=user_id)
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)

            # Create blacklist entry
            BlacklistedToken.objects.get_or_create(
                jti=jti, defaults={'user': user, 'token_type': token_type, 'expires_at': expires_at, 'reason': reason}
            )

            # If it's a refresh token, also invalidate the session
            if token_type == 'refresh':
                try:
                    session = UserSession.objects.get(refresh_token_jti=jti)
                    session.invalidate()
                except UserSession.DoesNotExist:
                    pass

            logger.info(f'Blacklisted {token_type} token {jti} for user {user_id}')
            return True

        except User.DoesNotExist:
            logger.warning('User not found for token blacklisting')
            return False
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f'Invalid token data for blacklisting: {e!s}')
            return False
        except Exception as e:
            logger.exception('Unexpected error blacklisting token')
            return False

    def logout_user(self, user: User, session_id: int = None) -> bool:
        """
        Logout user by invalidating all their sessions or specific session

        Args:
            user: User to logout
            session_id: Optional specific session to logout

        Returns:
            True if successful
        """
        try:
            if session_id:
                # Logout specific session
                sessions = UserSession.objects.filter(user=user, id=session_id, is_active=True)
            else:
                # Logout all sessions
                sessions = UserSession.objects.filter(user=user, is_active=True)

            for session in sessions:
                # Blacklist the refresh token
                self.blacklist_refresh_token_by_jti(session.refresh_token_jti, 'logout')
                session.invalidate()

            logger.info(f'Logged out user {user.id} ({sessions.count()} sessions)')
            return True

        except AttributeError as e:
            logger.error(f'Session attribute error during logout for user {user.id}: {e!s}')
            return False
        except Exception as e:
            logger.exception(f'Unexpected error during logout for user {user.id}')
            return False

    def blacklist_refresh_token_by_jti(self, jti: str, reason: str = 'logout') -> bool:
        """Blacklist refresh token by JTI"""
        try:
            session = UserSession.objects.get(refresh_token_jti=jti)

            BlacklistedToken.objects.get_or_create(
                jti=jti,
                defaults={
                    'user': session.user,
                    'token_type': 'refresh',
                    'expires_at': session.expires_at,
                    'reason': reason,
                },
            )
            return True
        except UserSession.DoesNotExist:
            return False

    def get_user_from_token(self, token: str, token_type: str = 'access') -> User | None:
        """
        Get user from valid token

        Args:
            token: JWT token
            token_type: Token type to verify

        Returns:
            User instance or None
        """
        payload = self.verify_token(token, token_type)
        if not payload:
            return None

        try:
            return User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return None

    def cleanup_expired_tokens(self) -> dict[str, int]:
        """
        Clean up expired blacklisted tokens and sessions

        Returns:
            Dict with cleanup counts
        """
        try:
            blacklisted_count = BlacklistedToken.cleanup_expired()
            sessions_count = UserSession.cleanup_expired()

            logger.info(f'Cleaned up {blacklisted_count} expired tokens and {sessions_count} sessions')
            return {'blacklisted_tokens': blacklisted_count, 'sessions': sessions_count}
        except AttributeError as e:
            logger.error(f'Model attribute error during cleanup: {e!s}')
            return {'blacklisted_tokens': 0, 'sessions': 0}
        except Exception as e:
            logger.exception('Unexpected error during cleanup')
            return {'blacklisted_tokens': 0, 'sessions': 0}

    def get_user_sessions(self, user: User) -> list:
        """Get all active sessions for user"""
        return UserSession.objects.filter(user=user, is_active=True).order_by('-last_activity')

    def decode_token_for_debug(self, token: str) -> dict[str, Any]:
        """
        Decode token without verification for debugging

        Args:
            token: JWT token

        Returns:
            Decoded payload
        """
        try:
            payload = jwt.decode(token, options={'verify_signature': False})

            # Add human-readable timestamps
            if 'iat' in payload:
                payload['iat_human'] = datetime.fromtimestamp(payload['iat']).isoformat()
            if 'exp' in payload:
                payload['exp_human'] = datetime.fromtimestamp(payload['exp']).isoformat()
                payload['is_expired'] = datetime.fromtimestamp(payload['exp']) < datetime.now()

            # Check if blacklisted
            jti = payload.get('jti')
            if jti:
                payload['is_blacklisted'] = BlacklistedToken.is_blacklisted(jti)

            return payload
        except (jwt.InvalidTokenError, ValueError, KeyError) as e:
            return {'error': f'Token decode error: {e!s}'}
        except Exception as e:
            return {'error': f'Unexpected error: {e!s}'}
