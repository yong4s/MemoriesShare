from __future__ import annotations

import logging
import secrets
import time
from typing import Any
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.tasks import send_verification_code_task
from apps.shared.utils.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from apps.accounts.models.custom_user import CustomUser

logger = logging.getLogger(__name__)


class PasswordlessService:
    CODE_KEY_PREFIX = 'passwordless:code'

    def __init__(
        self,
        user_dal: UserDAL | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.user_dal = user_dal or UserDAL()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.code_ttl_minutes = getattr(settings, 'PASSWORDLESS_CODE_TTL_MINUTES', 10)
        self.max_attempts = getattr(settings, 'PASSWORDLESS_MAX_ATTEMPTS', 5)

    def request_verification_code(self, email: str, ip_address: str | None = None) -> dict[str, Any]:
        normalized_email = self._normalize_email(email)
        normalized_ip = self._normalize_ip(ip_address)

        try:
            lockout_response = self._check_existing_lockout(normalized_email, normalized_ip)
            if lockout_response is not None:
                return lockout_response

            ip_rate_limit_response, ip_info = self._ensure_ip_rate_limit(normalized_ip)
            if ip_rate_limit_response is not None:
                return ip_rate_limit_response

            email_allowed, email_info = self.rate_limiter.check_email_rate_limit(normalized_email)
            if not email_allowed:
                retry_after = int(email_info.get('retry_after_seconds', 0))
                return self._build_rate_limit_response(
                    message=f'Too many verification requests. Try again in {retry_after} seconds.',
                    retry_after_seconds=retry_after,
                )

            verification_code = self._generate_code()
            self._store_verification_code(
                email=normalized_email,
                code=verification_code,
                ip_address=normalized_ip,
            )
            self._dispatch_verification_email(normalized_email, verification_code)

            logger.info('Verification code generated and queued for %s', normalized_email)
            return {
                'success': True,
                'message': f'Verification code sent to {normalized_email}',
                'expires_in_minutes': self.code_ttl_minutes,
                'rate_limit_info': {
                    'email_remaining': email_info.get('remaining', 0),
                    'ip_remaining': ip_info.get('remaining') if ip_info is not None else None,
                },
                'note': 'Check your email in a few moments. If using console backend, check Docker logs.',
            }
        except Exception as exc:
            logger.exception('Error requesting verification code for %s: %s', normalized_email, exc)
            return {
                'success': False,
                'error': 'internal_error',
                'message': 'Failed to send verification code. Please try again.',
            }

    def verify_code_and_authenticate(
        self,
        email: str,
        user_code: str,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        normalized_email = self._normalize_email(email)
        normalized_ip = self._normalize_ip(ip_address)
        normalized_code = user_code.strip()

        try:
            attempts_allowed, attempts_info = self.rate_limiter.check_verification_attempts(
                normalized_email,
                ip=normalized_ip,
            )
            if not attempts_allowed:
                retry_after = int(attempts_info.get('retry_after_seconds', 0))
                return {
                    'success': False,
                    'error': 'attempts_exceeded',
                    'message': f'Too many verification attempts. Try again in {retry_after} seconds.',
                    'retry_after_seconds': retry_after,
                }

            stored_code_data = self._load_verification_code_data(normalized_email)
            if stored_code_data is None:
                self.rate_limiter.increment_verification_attempts(normalized_email, ip=normalized_ip)
                return self._build_invalid_code_response()

            if not self._is_valid_submitted_code(stored_code_data, normalized_code):
                return self._handle_invalid_code_attempt(normalized_email, normalized_ip)

            self._cleanup_successful_verification(normalized_email, normalized_ip)
            user = self._get_or_create_passwordless_user(normalized_email)
            if not user.is_active:
                return {
                    'success': False,
                    'error': 'account_disabled',
                    'message': 'User account is disabled.',
                }

            access_token, refresh_token = self._generate_jwt_tokens(user)
            logger.info(
                'Successful passwordless authentication for %s from IP %s',
                normalized_email,
                normalized_ip,
            )
            return {
                'success': True,
                'message': 'Authentication successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_registered': user.is_registered,
                },
            }
        except Exception as exc:
            logger.exception('Error verifying code for %s: %s', normalized_email, exc)
            return {
                'success': False,
                'error': 'internal_error',
                'message': 'Verification failed. Please try again.',
            }

    def _check_existing_lockout(
        self,
        email: str,
        ip_address: str | None,
    ) -> dict[str, Any] | None:
        attempts_allowed, attempts_info = self.rate_limiter.check_verification_attempts(
            email,
            ip=ip_address,
        )
        if attempts_allowed:
            return None
        retry_after = int(attempts_info.get('retry_after_seconds', 0))
        return self._build_rate_limit_response(
            message=f'Too many failed attempts. Try again in {retry_after} seconds.',
            retry_after_seconds=retry_after,
        )

    def _ensure_ip_rate_limit(
        self,
        ip_address: str | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if not ip_address:
            return None, None

        ip_allowed, ip_info = self.rate_limiter.check_ip_rate_limit(ip_address)
        if ip_allowed:
            return None, ip_info

        retry_after = int(ip_info.get('retry_after_seconds', 0))
        return (
            self._build_rate_limit_response(
                message=f'Too many requests from this IP. Try again in {retry_after} seconds.',
                retry_after_seconds=retry_after,
            ),
            ip_info,
        )

    def _build_rate_limit_response(self, message: str, retry_after_seconds: int) -> dict[str, Any]:
        return {
            'success': False,
            'error': 'rate_limit_exceeded',
            'message': message,
            'retry_after_seconds': retry_after_seconds,
        }

    def _build_invalid_code_response(self, attempts_remaining: int | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {
            'success': False,
            'error': 'invalid_code',
            'message': 'Invalid or expired verification code.',
        }
        if attempts_remaining is not None:
            response['attempts_remaining'] = attempts_remaining
            response['message'] = f'Invalid verification code. {attempts_remaining} attempts remaining.'
        return response

    def _store_verification_code(self, email: str, code: str, ip_address: str | None) -> None:
        payload = {
            'code_hash': make_password(code),
            'email': email,
            'created_at': int(time.time()),
            'ip_address': ip_address,
        }
        cache.set(self._build_code_key(email), payload, self.code_ttl_minutes * 60)

    def _load_verification_code_data(self, email: str) -> dict[str, Any] | None:
        payload = cache.get(self._build_code_key(email))
        if payload is None:
            return None
        if not isinstance(payload, dict):
            cache.delete(self._build_code_key(email))
            logger.warning('Malformed passwordless code payload for %s was deleted', email)
            return None
        return payload

    def _is_valid_submitted_code(self, stored_data: dict[str, Any], user_code: str) -> bool:
        stored_hash = stored_data.get('code_hash')
        if not isinstance(stored_hash, str) or not stored_hash:
            return False
        return check_password(user_code, stored_hash)

    def _handle_invalid_code_attempt(self, email: str, ip_address: str | None) -> dict[str, Any]:
        attempts = self.rate_limiter.increment_verification_attempts(email, ip=ip_address)
        if attempts >= self.max_attempts:
            cache.delete(self._build_code_key(email))
            logger.warning('Max verification attempts reached for %s', email)
        return self._build_invalid_code_response(
            attempts_remaining=max(self.max_attempts - attempts, 0),
        )

    def _cleanup_successful_verification(self, email: str, ip_address: str | None) -> None:
        cache.delete(self._build_code_key(email))
        self.rate_limiter.reset_verification_attempts(email, ip=ip_address)

    def _dispatch_verification_email(self, email: str, code: str) -> None:
        send_verification_code_task.delay(email, code, self.code_ttl_minutes)

    def _generate_code(self) -> str:
        return f'{secrets.randbelow(1000000):06d}'

    def _get_or_create_passwordless_user(self, email: str) -> CustomUser:
        existing_user = self.user_dal.get_by_email(email, registered_only=False)
        if existing_user:
            return existing_user

        with transaction.atomic():
            display_name = email.split('@', maxsplit=1)[0]
            user = self.user_dal.create_guest_user(guest_name=display_name, email=email)
            logger.info('Created new passwordless user: %s', email)
            return user

    @staticmethod
    def _generate_jwt_tokens(user: CustomUser) -> tuple[str, str]:
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token), str(refresh)

    def _build_code_key(self, email: str) -> str:
        return f'{self.CODE_KEY_PREFIX}:{email}'

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.lower().strip()

    @staticmethod
    def _normalize_ip(ip_address: str | None) -> str | None:
        if not ip_address:
            return None
        return ip_address.strip()
