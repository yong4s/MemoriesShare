"""
Base Cache Client - Pure Infrastructure Layer

Provides low-level cache operations without domain knowledge.
Handles Redis/Django cache backend interactions safely.
"""

import json
import logging
from typing import Any, Dict

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


class BaseCacheClient:
    """
    Low-level cache client with no domain knowledge.
    
    Responsibilities:
    - Core cache operations (get, set, delete)
    - Safe pattern-based deletion using SCAN
    - Error handling and logging
    - Statistics tracking (hits/misses/errors)
    
    Does NOT know about:
    - Events, Users, or other domain entities
    - Business-specific cache keys or TTL strategies
    - Domain-specific invalidation logic
    """
    
    def __init__(self):
        self.cache = cache
        self.logger = logger
        self._hits = 0
        self._misses = 0
        self._errors = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with statistics tracking."""
        try:
            value = self.cache.get(key, default)

            if value is not default:
                self._hits += 1
                self.logger.debug(f'Cache HIT: {key}')
            else:
                self._misses += 1
                self.logger.debug(f'Cache MISS: {key}')

            return value

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache GET error for key {key}: {e}')
            return default

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Set value in cache with optional timeout."""
        try:
            # Normalize serializable types
            if isinstance(value, dict | list | str | int | float | bool):
                payload = value
            else:
                # Convert to JSON serializable structure
                payload = json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))

            success = self.cache.set(key, payload, timeout)
            if success:
                self.logger.debug(f'Cache SET: {key} (timeout: {timeout})')
            return bool(success)

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache SET error for key {key}: {e}')
            return False

    def delete(self, key: str) -> bool:
        """Delete single key from cache."""
        try:
            success = self.cache.delete(key)
            self.logger.debug(f'Cache DELETE: {key} (success: {success})')
            return success

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache DELETE error for key {key}: {e}')
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern using django_redis native delete_pattern.

        Args:
            pattern: Redis glob pattern (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            if hasattr(self.cache, 'delete_pattern'):
                deleted = self.cache.delete_pattern(pattern)
                self.logger.info(f'Cache DELETE_PATTERN: {pattern} (deleted: {deleted} keys)')
                return deleted or 0

            self.logger.warning(f'Pattern deletion not supported for current cache backend, pattern: {pattern}')
            return 0

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache DELETE_PATTERN error for pattern {pattern}: {e}')
            return 0

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys at once."""
        try:
            if not keys:
                return {}

            result = self.cache.get_many(keys)

            # Update statistics
            self._hits += len(result)
            self._misses += len(keys) - len(result)

            self.logger.debug(f'Cache GET_MANY: {len(keys)} keys, {len(result)} found')
            return result

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache GET_MANY error: {e}')
            return {}

    def set_many(self, mapping: dict[str, Any], timeout: int | None = None) -> bool:
        """Set multiple key-value pairs at once."""
        try:
            if not mapping:
                return False

            # Serialize complex objects
            processed_mapping = {}
            for key, value in mapping.items():
                if hasattr(value, '__dict__') and not isinstance(value, str | int | float | bool | list | dict):
                    value = json.dumps(value, cls=DjangoJSONEncoder, default=str)
                processed_mapping[key] = value

            success = self.cache.set_many(processed_mapping, timeout)
            self.logger.debug(f'Cache SET_MANY: {len(processed_mapping)} keys (timeout: {timeout})')
            return success

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache SET_MANY error: {e}')
            return False

    def get_stats(self) -> dict[str, int | float]:
        """Get cache operation statistics."""
        total_operations = self._hits + self._misses
        hit_rate = (self._hits / total_operations * 100) if total_operations > 0 else 0

        return {
            'hits': self._hits,
            'misses': self._misses,
            'errors': self._errors,
            'total_operations': total_operations,
            'hit_rate_percentage': round(hit_rate, 2),
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self.logger.info('Cache statistics reset')

    def health_check(self) -> dict[str, Any]:
        """Perform cache backend health check."""
        try:
            # Test basic operations
            test_key = 'health:check:test'
            test_value = 'test_value'

            # Test set/get/delete
            self.cache.set(test_key, test_value, 10)
            retrieved = self.cache.get(test_key)
            self.cache.delete(test_key)

            success = retrieved == test_value

            return {
                'status': 'healthy' if success else 'degraded',
                'connection': 'ok' if success else 'error',
                'test_successful': success,
                'statistics': self.get_stats(),
            }

        except Exception as e:
            self.logger.exception(f'Cache health check failed: {e}')
            return {
                'status': 'unhealthy',
                'connection': 'error',
                'test_successful': False,
                'error': str(e),
            }


# Module-level singleton for shared use across application
base_cache_client = BaseCacheClient()