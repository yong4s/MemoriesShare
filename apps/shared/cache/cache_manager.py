import json
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder

from apps.shared.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self):
        self.cache = cache
        self.logger = logger
        self.keys = CacheKeys
        self._hits = 0
        self._misses = 0
        self._errors = 0

    def get(self, key: str, default: Any = None) -> Any:
        try:
            if not self.keys.validate_key(key):
                self.logger.warning(f'Invalid cache key format: {key}')
                return default

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
        try:
            if not self.keys.validate_key(key):
                self.logger.warning('Invalid key')
                return False

            # Normalize common serializable types
            if isinstance(value, dict | list | str | int | float | bool):
                payload = value
            else:
                # convert to JSON serializable structure first
                payload = json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))

            success = self.cache.set(key, payload, timeout)
            if success:
                self.logger.debug(...)
            return bool(success)

        except Exception:
            self._errors += 1
            self.logger.exception('Cache SET error')
            return False

    def delete(self, key: str) -> bool:
        try:
            success = self.cache.delete(key)
            self.logger.debug(f'Cache DELETE: {key} (success: {success})')
            return success

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache DELETE error for key {key}: {e}')
            return False

    def delete_pattern(self, pattern: str) -> int:
        try:
            # Get Redis client for pattern operations
            redis_client = self.cache._cache.get_client(1)
            keys = redis_client.keys(pattern)

            if keys:
                deleted = redis_client.delete(*keys)
                self.logger.info(f'Cache DELETE_PATTERN: {pattern} (deleted: {deleted} keys)')
                return deleted
            self.logger.debug(f'Cache DELETE_PATTERN: {pattern} (no keys found)')
            return 0

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache DELETE_PATTERN error for pattern {pattern}: {e}')
            return 0

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        try:
            # Filter out invalid keys
            valid_keys = [key for key in keys if self.keys.validate_key(key)]
            if len(valid_keys) != len(keys):
                invalid_keys = set(keys) - set(valid_keys)
                self.logger.warning(f'Invalid cache keys filtered out: {invalid_keys}')

            if not valid_keys:
                return {}

            result = self.cache.get_many(valid_keys)

            # Update statistics
            self._hits += len(result)
            self._misses += len(valid_keys) - len(result)

            self.logger.debug(f'Cache GET_MANY: {len(valid_keys)} keys, {len(result)} found')
            return result

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache GET_MANY error: {e}')
            return {}

    def set_many(self, mapping: dict[str, Any], timeout: int | None = None) -> bool:
        try:
            # Filter out invalid keys and serialize values
            valid_mapping = {}
            for key, value in mapping.items():
                if not self.keys.validate_key(key):
                    self.logger.warning(f'Invalid cache key skipped: {key}')
                    continue

                # Serialize complex objects
                if hasattr(value, '__dict__') and not isinstance(value, str | int | float | bool | list | dict):
                    value = json.dumps(value, cls=DjangoJSONEncoder, default=str)

                valid_mapping[key] = value

            if not valid_mapping:
                return False

            success = self.cache.set_many(valid_mapping, timeout)
            self.logger.debug(f'Cache SET_MANY: {len(valid_mapping)} keys (timeout: {timeout})')
            return success

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Cache SET_MANY error: {e}')
            return False

    def invalidate_user_cache(self, user_id: int, cache_types: list[str] | None = None) -> int:
        try:
            if cache_types:
                # Invalidate specific types
                deleted = 0
                for cache_type in cache_types:
                    pattern = f'{self.keys.USER_PREFIX}:{user_id}:{cache_type}:*'
                    deleted += self.delete_pattern(pattern)
            else:
                # Invalidate all user cache
                pattern = self.keys.user_pattern(user_id)
                deleted = self.delete_pattern(pattern)

            self.logger.info(f'Invalidated user cache for user {user_id}: {deleted} keys')
            return deleted

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Error invalidating user cache for user {user_id}: {e}')
            return 0

    def invalidate_event_cache(self, event_uuid: str, cache_types: list[str] | None = None) -> int:
        try:
            if cache_types:
                # Invalidate specific types
                deleted = 0
                for cache_type in cache_types:
                    pattern = f'{self.keys.EVENT_PREFIX}:{event_uuid}:{cache_type}:*'
                    deleted += self.delete_pattern(pattern)
            else:
                # Invalidate all event cache
                pattern = self.keys.event_pattern(event_uuid)
                deleted = self.delete_pattern(pattern)

            self.logger.info(f'Invalidated event cache for event {event_uuid}: {deleted} keys')
            return deleted

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Error invalidating event cache for event {event_uuid}: {e}')
            return 0

    def warm_event_cache(self, event_data: dict[str, Any], event_uuid: str) -> bool:
        try:
            {
                self.keys.event_detail(event_uuid): event_data,
                self.keys.event_statistics(event_uuid): event_data.get('statistics', {}),
            }

            # Different TTLs for different data types
            success = True
            success &= self.set(self.keys.event_detail(event_uuid), event_data, timeout=600)  # 10 min
            success &= self.set(
                self.keys.event_statistics(event_uuid),
                event_data.get('statistics', {}),
                timeout=300,
            )  # 5 min

            self.logger.info(f'Warmed cache for event {event_uuid}')
            return success

        except Exception as e:
            self._errors += 1
            self.logger.exception(f'Error warming event cache for {event_uuid}: {e}')
            return False

    def get_stats(self) -> dict[str, int | float]:
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
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self.logger.info('Cache statistics reset')

    def health_check(self) -> dict[str, Any]:
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
