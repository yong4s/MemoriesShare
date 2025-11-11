"""
Cache Manager for Redis Operations

Provides high-level abstraction over Django's Redis cache backend
with logging, error handling, and specialized event/user caching operations.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder

from .cache_keys import CacheKeys


logger = logging.getLogger(__name__)


class CacheManager:
    """
    High-level Redis cache manager with error handling and logging.
    
    Provides abstraction over Django cache with additional features:
    - Automatic JSON serialization for complex objects
    - Batch operations for performance
    - Pattern-based deletion for bulk invalidation  
    - Cache hit/miss statistics
    - Error handling and fallback behavior
    """

    def __init__(self):
        self.cache = cache
        self.logger = logger
        self.keys = CacheKeys
        
        # Statistics tracking
        self._hits = 0
        self._misses = 0
        self._errors = 0

    # =============================================================================
    # BASIC CACHE OPERATIONS
    # =============================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with error handling and statistics.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            if not self.keys.validate_key(key):
                self.logger.warning(f"Invalid cache key format: {key}")
                return default

            value = self.cache.get(key, default)
            
            if value is not default:
                self._hits += 1
                self.logger.debug(f"Cache HIT: {key}")
            else:
                self._misses += 1
                self.logger.debug(f"Cache MISS: {key}")
                
            return value
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache GET error for key {key}: {e}")
            return default

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        try:
            if not self.keys.validate_key(key):
                self.logger.warning("Invalid key")
                return False

            # Normalize common serializable types
            if isinstance(value, (dict, list, str, int, float, bool)):
                payload = value
            else:
                # convert to JSON serializable structure first
                payload = json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))

            success = self.cache.set(key, payload, timeout)
            if success:
                self.logger.debug(...)
            return bool(success)

        except Exception as e:
            self._errors += 1
            self.logger.exception("Cache SET error")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete single cache key.
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if key was deleted
        """
        try:
            success = self.cache.delete(key)
            self.logger.debug(f"Cache DELETE: {key} (success: {success})")
            return success
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache DELETE error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Redis pattern (e.g., 'user:123:*')
            
        Returns:
            int: Number of keys deleted
        """
        try:
            # Get Redis client for pattern operations
            redis_client = self.cache._cache.get_client(1)
            keys = redis_client.keys(pattern)
            
            if keys:
                deleted = redis_client.delete(*keys)
                self.logger.info(f"Cache DELETE_PATTERN: {pattern} (deleted: {deleted} keys)")
                return deleted
            else:
                self.logger.debug(f"Cache DELETE_PATTERN: {pattern} (no keys found)")
                return 0
                
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0

    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values in single operation.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict mapping keys to values
        """
        try:
            # Filter out invalid keys
            valid_keys = [key for key in keys if self.keys.validate_key(key)]
            if len(valid_keys) != len(keys):
                invalid_keys = set(keys) - set(valid_keys)
                self.logger.warning(f"Invalid cache keys filtered out: {invalid_keys}")

            if not valid_keys:
                return {}

            result = self.cache.get_many(valid_keys)
            
            # Update statistics
            self._hits += len(result)
            self._misses += len(valid_keys) - len(result)
            
            self.logger.debug(f"Cache GET_MANY: {len(valid_keys)} keys, {len(result)} found")
            return result
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache GET_MANY error: {e}")
            return {}

    def set_many(self, mapping: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """
        Set multiple values in single operation.
        
        Args:
            mapping: Dict of key-value pairs
            timeout: TTL in seconds (None for default)
            
        Returns:
            bool: True if all operations successful
        """
        try:
            # Filter out invalid keys and serialize values
            valid_mapping = {}
            for key, value in mapping.items():
                if not self.keys.validate_key(key):
                    self.logger.warning(f"Invalid cache key skipped: {key}")
                    continue
                    
                # Serialize complex objects
                if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict)):
                    value = json.dumps(value, cls=DjangoJSONEncoder, default=str)
                    
                valid_mapping[key] = value

            if not valid_mapping:
                return False

            success = self.cache.set_many(valid_mapping, timeout)
            self.logger.debug(f"Cache SET_MANY: {len(valid_mapping)} keys (timeout: {timeout})")
            return success
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache SET_MANY error: {e}")
            return False

    # =============================================================================
    # SPECIALIZED EVENT/USER OPERATIONS
    # =============================================================================

    def invalidate_user_cache(self, user_id: int, cache_types: Optional[List[str]] = None) -> int:
        """
        Invalidate all or specific user cache entries.
        
        Args:
            user_id: User ID
            cache_types: Specific cache types to invalidate (None for all)
            
        Returns:
            int: Number of keys deleted
        """
        try:
            if cache_types:
                # Invalidate specific types
                deleted = 0
                for cache_type in cache_types:
                    pattern = f"{self.keys.USER_PREFIX}:{user_id}:{cache_type}:*"
                    deleted += self.delete_pattern(pattern)
            else:
                # Invalidate all user cache
                pattern = self.keys.user_pattern(user_id)
                deleted = self.delete_pattern(pattern)
                
            self.logger.info(f"Invalidated user cache for user {user_id}: {deleted} keys")
            return deleted
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error invalidating user cache for user {user_id}: {e}")
            return 0

    def invalidate_event_cache(self, event_uuid: str, cache_types: Optional[List[str]] = None) -> int:
        """
        Invalidate all or specific event cache entries.
        
        Args:
            event_uuid: Event UUID
            cache_types: Specific cache types to invalidate (None for all)
            
        Returns:
            int: Number of keys deleted
        """
        try:
            if cache_types:
                # Invalidate specific types
                deleted = 0
                for cache_type in cache_types:
                    pattern = f"{self.keys.EVENT_PREFIX}:{event_uuid}:{cache_type}:*"
                    deleted += self.delete_pattern(pattern)
            else:
                # Invalidate all event cache
                pattern = self.keys.event_pattern(event_uuid)
                deleted = self.delete_pattern(pattern)
                
            self.logger.info(f"Invalidated event cache for event {event_uuid}: {deleted} keys")
            return deleted
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error invalidating event cache for event {event_uuid}: {e}")
            return 0

    def warm_event_cache(self, event_data: Dict[str, Any], event_uuid: str) -> bool:
        """
        Pre-populate event-related cache entries.
        
        Args:
            event_data: Event data to cache
            event_uuid: Event UUID
            
        Returns:
            bool: True if warming successful
        """
        try:
            cache_entries = {
                self.keys.event_detail(event_uuid): event_data,
                self.keys.event_statistics(event_uuid): event_data.get('statistics', {}),
            }
            
            # Different TTLs for different data types
            success = True
            success &= self.set(self.keys.event_detail(event_uuid), event_data, timeout=600)  # 10 min
            success &= self.set(self.keys.event_statistics(event_uuid), event_data.get('statistics', {}), timeout=300)  # 5 min
            
            self.logger.info(f"Warmed cache for event {event_uuid}")
            return success
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error warming event cache for {event_uuid}: {e}")
            return False

    # =============================================================================
    # MONITORING & STATISTICS
    # =============================================================================

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get cache performance statistics.
        
        Returns:
            Dict with hit/miss rates and error counts
        """
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
        """Reset cache statistics counters."""
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self.logger.info("Cache statistics reset")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform cache health check.
        
        Returns:
            Dict with health status and connection info
        """
        try:
            # Test basic operations
            test_key = "health:check:test"
            test_value = "test_value"
            
            # Test set/get/delete
            self.cache.set(test_key, test_value, 10)
            retrieved = self.cache.get(test_key)
            self.cache.delete(test_key)
            
            success = retrieved == test_value
            
            return {
                'status': 'healthy' if success else 'degraded',
                'connection': 'ok' if success else 'error',
                'test_successful': success,
                'statistics': self.get_stats()
            }
            
        except Exception as e:
            self.logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connection': 'error',
                'test_successful': False,
                'error': str(e)
            }
