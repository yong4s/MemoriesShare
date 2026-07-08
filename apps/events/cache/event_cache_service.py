"""
Event Cache Service - Domain-Specific Cache Operations

Handles all caching logic specifically for the Events domain.
Knows about event business rules, cache keys, TTL strategies, and invalidation patterns.
"""

import logging
from typing import Any
from typing import Dict
from typing import List

from apps.shared.cache.base_cache_client import base_cache_client
from apps.shared.cache.base_cache_client import BaseCacheClient
from apps.shared.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class EventCacheService:
    """
    Domain-specific cache service for Events.

    Responsibilities:
    - Event-specific cache key generation
    - Event-specific TTL strategies
    - Event-specific invalidation patterns
    - Event cache warming strategies

    Uses BaseCacheClient for actual cache operations.
    """

    def __init__(self, cache_client: BaseCacheClient | None = None):
        self.cache = cache_client or base_cache_client
        self.keys = CacheKeys

    @staticmethod
    def _is_model_instance(value: Any) -> bool:
        return hasattr(value, '_meta') and hasattr(value, 'pk')

    # Event Detail Caching
    def get_cached_event_detail(self, event_uuid: str) -> Any:
        """Get cached event detail by UUID."""
        key = self.keys.event_detail(event_uuid)
        return self.cache.get(key)

    def cache_event_detail(self, event_uuid: str, event_data: dict[str, Any], timeout: int = 600) -> bool:
        """
        Cache event detail with business-appropriate TTL.

        Default: 10 minutes (events don't change frequently)
        """
        key = self.keys.event_detail(event_uuid)
        success = self.cache.set(key, event_data, timeout)
        if success:
            logger.debug(f'Cached event detail: {event_uuid}')
        return success

    def invalidate_event_detail(self, event_uuid: str) -> bool:
        """Invalidate cached event detail."""
        key = self.keys.event_detail(event_uuid)
        return self.cache.delete(key)

    # Event Statistics Caching
    def get_cached_event_statistics(self, event_uuid: str) -> Any:
        """Get cached event statistics by UUID."""
        key = self.keys.event_statistics(event_uuid)
        return self.cache.get(key)

    def cache_event_statistics(self, event_uuid: str, statistics: dict[str, Any], timeout: int = 300) -> bool:
        """
        Cache event statistics with shorter TTL.

        Default: 5 minutes (statistics change more frequently)
        """
        key = self.keys.event_statistics(event_uuid)
        success = self.cache.set(key, statistics, timeout)
        if success:
            logger.debug(f'Cached event statistics: {event_uuid}')
        return success

    def invalidate_event_statistics(self, event_uuid: str) -> bool:
        """Invalidate cached event statistics."""
        key = self.keys.event_statistics(event_uuid)
        return self.cache.delete(key)

    # Event Participants Caching
    def get_cached_event_participants(
        self, event_uuid: str, role_filter: str | None = None, rsvp_filter: str | None = None
    ) -> Any:
        """Get cached event participants with optional filters."""
        key = self.keys.event_participants(event_uuid, role_filter, rsvp_filter)
        return self.cache.get(key)

    def cache_event_participants(
        self,
        event_uuid: str,
        participants: list[Any],
        role_filter: str | None = None,
        rsvp_filter: str | None = None,
        timeout: int = 180,
    ) -> bool:
        """
        Cache event participants with filters.

        Default: 3 minutes (participant status can change quickly)
        """
        key = self.keys.event_participants(event_uuid, role_filter, rsvp_filter)
        success = self.cache.set(key, participants, timeout)
        if success:
            logger.debug(f'Cached event participants: {event_uuid} (filters: {role_filter}, {rsvp_filter})')
        return success

    def invalidate_event_participants(self, event_uuid: str) -> int:
        """Invalidate all cached participants for an event (all filter combinations)."""
        pattern = f'{self.keys.EVENT_PREFIX}:{event_uuid}:participants:*'
        count = self.cache.delete_pattern(pattern)
        logger.debug(f'Invalidated {count} participant cache entries for event {event_uuid}')
        return count

    # Bulk Event Operations
    def invalidate_event_cache(self, event_uuid: str, cache_types: list[str] | None = None) -> int:
        """
        Invalidate specific types of event cache or all event cache.

        Args:
            event_uuid: Event UUID
            cache_types: List of cache types to invalidate (e.g., ['detail', 'statistics'])
                        If None, invalidates all cache for this event

        Returns:
            Number of cache entries deleted
        """
        try:
            if cache_types:
                # Invalidate specific types
                deleted = 0
                for cache_type in cache_types:
                    if cache_type == 'detail':
                        if self.invalidate_event_detail(event_uuid):
                            deleted += 1
                    elif cache_type == 'statistics':
                        if self.invalidate_event_statistics(event_uuid):
                            deleted += 1
                    elif cache_type == 'participants':
                        deleted += self.invalidate_event_participants(event_uuid)
                    else:
                        # Generic pattern-based invalidation
                        pattern = f'{self.keys.EVENT_PREFIX}:{event_uuid}:{cache_type}:*'
                        deleted += self.cache.delete_pattern(pattern)
            else:
                # Invalidate all event cache
                pattern = self.keys.event_pattern(event_uuid)
                deleted = self.cache.delete_pattern(pattern)

            logger.info(f'Invalidated event cache for event {event_uuid}: {deleted} keys (types: {cache_types})')
            return deleted

        except Exception as e:
            logger.exception(f'Error invalidating event cache for event {event_uuid}: {e}')
            return 0

    # Read-Through Pattern Support
    def get_or_set_event_detail(self, event_uuid: str, fetch_func, timeout: int = 600) -> Any:
        """
        Get event detail from cache, or fetch and cache if not found.

        Args:
            event_uuid: Event UUID
            fetch_func: Function to call if cache miss (should return event data)
            timeout: Cache TTL in seconds

        Returns:
            Event data from cache or freshly fetched
        """
        # Try cache first
        cached_data = self.get_cached_event_detail(event_uuid)
        if cached_data is not None:
            if self._is_model_instance(cached_data):
                return cached_data

            # Defensive cleanup: old cache payloads can store model instances as strings.
            self.invalidate_event_detail(event_uuid)

        # Cache miss - fetch from source
        fresh_data = fetch_func()
        if fresh_data is not None:
            # Model instances should not be cached through JSON serialization layer.
            if not self._is_model_instance(fresh_data):
                self.cache_event_detail(event_uuid, fresh_data, timeout)
        return fresh_data

    def get_or_set_event_statistics(self, event_uuid: str, fetch_func, timeout: int = 300) -> Any:
        """
        Get event statistics from cache, or fetch and cache if not found.

        Args:
            event_uuid: Event UUID
            fetch_func: Function to call if cache miss (should return statistics data)
            timeout: Cache TTL in seconds

        Returns:
            Statistics data from cache or freshly fetched
        """
        # Try cache first
        cached_stats = self.get_cached_event_statistics(event_uuid)
        if cached_stats is not None:
            return cached_stats

        # Cache miss - fetch from source
        fresh_stats = fetch_func()
        if fresh_stats is not None:
            self.cache_event_statistics(event_uuid, fresh_stats, timeout)
        return fresh_stats


# Module-level singleton for shared use
event_cache_service = EventCacheService()
