from __future__ import annotations

import hashlib
import logging
import time
import uuid

from django.conf import settings
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

# Atomic sliding-window check-and-admit. Doing evict + count + conditional add in
# one Lua script closes the check-then-add race where N concurrent requests all
# observe count < limit before any of them adds its member.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local member = ARGV[5]

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
    return {0, count}
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl)
return {1, count + 1}
"""


class RateLimiter:
    """Redis-based rate limiter with configurable rules for passwordless auth."""

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client or get_redis_connection('default')

        cache_conf = settings.CACHES['default']
        prefix = cache_conf.get('KEY_PREFIX', '')
        version = cache_conf.get('VERSION', 1)
        self._namespace = f'{prefix}:{version}:' if prefix else f'{version}:'

        self.default_settings = {
            'email_requests_limit': getattr(settings, 'PASSWORDLESS_EMAIL_RATE_LIMIT', 5),
            'email_window_minutes': getattr(settings, 'PASSWORDLESS_EMAIL_WINDOW_MINUTES', 15),
            'ip_requests_limit': getattr(settings, 'PASSWORDLESS_IP_RATE_LIMIT', 20),
            'ip_window_minutes': getattr(settings, 'PASSWORDLESS_IP_WINDOW_MINUTES', 15),
            'verification_attempts_limit': getattr(settings, 'PASSWORDLESS_VERIFICATION_ATTEMPTS', 5),
            'failed_lockout_minutes': getattr(settings, 'PASSWORDLESS_FAILED_LOCKOUT_MINUTES', 60),
        }

    def check_email_rate_limit(self, email: str) -> tuple[bool, dict]:
        key = self._namespaced(f'passwordless:rate:email:{email.lower()}')
        window_seconds = self.default_settings['email_window_minutes'] * 60
        limit = self.default_settings['email_requests_limit']
        return self._check_rate_limit(key, limit, window_seconds, 'email')

    def check_ip_rate_limit(self, ip_address: str) -> tuple[bool, dict]:
        key = self._namespaced(f'passwordless:rate:ip:{ip_address}')
        window_seconds = self.default_settings['ip_window_minutes'] * 60
        limit = self.default_settings['ip_requests_limit']
        return self._check_rate_limit(key, limit, window_seconds, 'ip')

    def check_custom_rate_limit(
        self,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        key = self._namespaced(f'ratelimit:{scope}:{identifier}')
        return self._check_rate_limit(key, limit, window_seconds, scope)

    def check_verification_attempts(
        self,
        email: str,
        ip: str | None = None,
    ) -> tuple[bool, dict]:
        key = self._build_attempts_key(email, ip)
        limit = self.default_settings['verification_attempts_limit']

        try:
            current_attempts = self.redis.get(key)
            attempts = int(current_attempts) if current_attempts else 0

            if attempts >= limit:
                ttl = self.redis.ttl(key)
                if ttl > 0:
                    return False, {
                        'allowed': False,
                        'attempts': attempts,
                        'limit': limit,
                        'retry_after_seconds': ttl,
                        'reason': 'verification_attempts_exceeded',
                    }
        except Exception:
            logger.exception('Error checking verification attempts for %s', email)
            return False, {
                'allowed': False,
                'error': 'service_unavailable',
                'message': 'Verification service temporarily unavailable.',
            }

        return True, {
            'allowed': True,
            'attempts': attempts,
            'limit': limit,
            'remaining': limit - attempts,
        }

    def increment_verification_attempts(
        self,
        email: str,
        ip: str | None = None,
    ) -> int:
        key = self._build_attempts_key(email, ip)
        lockout_seconds = self.default_settings['failed_lockout_minutes'] * 60

        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, lockout_seconds)
            results = pipe.execute()
        except Exception:
            logger.exception('Error incrementing verification attempts for %s', email)
            return 1

        new_count = results[0]
        logger.info('Verification attempts incremented for %s: %s', email, new_count)
        return new_count

    def reset_verification_attempts(
        self,
        email: str,
        ip: str | None = None,
    ) -> bool:
        key = self._build_attempts_key(email, ip)

        try:
            result = self.redis.delete(key)
        except Exception:
            logger.exception('Error resetting verification attempts for %s', email)
            return False

        logger.info('Verification attempts reset for %s', email)
        return bool(result)

    def _build_attempts_key(self, email: str, ip: str | None = None) -> str:  # noqa: ARG002
        # Lock failed verification attempts strictly per email — NOT per IP.
        # Keying by a spoofable X-Forwarded-For let an attacker reset the lockout
        # by rotating IPs and multiply guesses against one email. The `ip` arg is
        # kept for call-site compatibility but intentionally excluded from the key.
        email_digest = hashlib.sha256(email.lower().strip().encode('utf-8')).hexdigest()[:16]
        return self._namespaced(f'passwordless:attempts:{email_digest}')

    def _namespaced(self, key: str) -> str:
        return f'{self._namespace}{key}'

    def _check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        limit_type: str,
    ) -> tuple[bool, dict]:
        try:
            now = time.time()
            window_start = now - window_seconds
            member = f'{time.time_ns()}-{uuid.uuid4().hex}'

            allowed_flag, current_count = self.redis.eval(
                _SLIDING_WINDOW_LUA,
                1,
                key,
                now,
                window_start,
                limit,
                window_seconds,
                member,
            )

            if not allowed_flag:
                ttl = self.redis.ttl(key)
                return False, {
                    'allowed': False,
                    'current_count': current_count,
                    'limit': limit,
                    'window_seconds': window_seconds,
                    'retry_after_seconds': max(ttl, 0),
                    'limit_type': limit_type,
                }

            return True, {
                'allowed': True,
                'current_count': current_count,
                'limit': limit,
                'remaining': limit - current_count,
                'window_seconds': window_seconds,
                'limit_type': limit_type,
            }
        except Exception:
            logger.exception('Error checking rate limit for key %s', key)
            return False, {
                'allowed': False,
                'error': 'service_unavailable',
                'message': 'Rate limit service temporarily unavailable.',
            }
