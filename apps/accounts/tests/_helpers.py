"""Shared test helpers for accounts test suite."""

from __future__ import annotations


class FakeRateLimiter:
    """In-memory stand-in for RateLimiter used by view tests.

    Counters are kept per (scope, identifier). Each call increments the
    counter; when it exceeds the passed `limit` the checker returns
    `(False, info)`. Reset between tests via fresh instances.
    """

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    def _hit(self, scope: str, identifier: str, limit: int):
        key = (scope, identifier)
        self._counts[key] = self._counts.get(key, 0) + 1
        count = self._counts[key]
        if count > limit:
            return False, {
                'allowed': False,
                'current_count': count,
                'limit': limit,
                'retry_after_seconds': 60,
                'limit_type': scope,
            }
        return True, {
            'allowed': True,
            'current_count': count,
            'limit': limit,
            'remaining': limit - count,
            'limit_type': scope,
        }

    def check_custom_rate_limit(self, scope: str, identifier: str, limit: int, window_seconds: int):  # noqa: ARG002
        return self._hit(scope, identifier, limit)

    def check_email_rate_limit(self, email: str):  # noqa: ARG002, PLR6301
        return True, {'remaining': 10}

    def check_ip_rate_limit(self, ip_address: str):  # noqa: ARG002, PLR6301
        return True, {'remaining': 10}

    def check_verification_attempts(self, email: str):  # noqa: ARG002, PLR6301
        return True, {'remaining': 5}

    def increment_verification_attempts(self, email: str):  # noqa: ARG002, PLR6301
        return 1

    def reset_verification_attempts(self, email: str):  # noqa: ARG002, PLR6301
        return True
