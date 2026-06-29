"""
User Cache Service - Domain-Specific Cache Operations

Handles all caching logic specifically for the Users/Accounts domain.
Knows about user business rules, cache keys, TTL strategies, and invalidation patterns.
"""

import logging
from typing import Any, Dict, List

from apps.shared.cache.base_cache_client import BaseCacheClient, base_cache_client
from apps.shared.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class UserCacheService:
    """
    Domain-specific cache service for Users/Accounts.
    
    Responsibilities:
    - User-specific cache key generation
    - User-specific TTL strategies  
    - User-specific invalidation patterns
    - User session and profile caching
    
    Uses BaseCacheClient for actual cache operations.
    """
    
    def __init__(self, cache_client: BaseCacheClient = None):
        self.cache = cache_client or base_cache_client
        self.keys = CacheKeys

    # User Profile Caching
    def get_cached_user_profile(self, user_id: int) -> Any:
        """Get cached user profile by user ID."""
        key = self.keys.user_profile(user_id)
        return self.cache.get(key)

    def cache_user_profile(self, user_id: int, profile_data: Dict[str, Any], timeout: int = 900) -> bool:
        """
        Cache user profile with appropriate TTL.
        
        Default: 15 minutes (profiles don't change very frequently)
        """
        key = self.keys.user_profile(user_id)
        success = self.cache.set(key, profile_data, timeout)
        if success:
            logger.debug(f'Cached user profile: {user_id}')
        return success

    def invalidate_user_profile(self, user_id: int) -> bool:
        """Invalidate cached user profile."""
        key = self.keys.user_profile(user_id)
        return self.cache.delete(key)

    # User Events List Caching
    def get_cached_user_events(self, user_id: int, page: int = 1, page_size: int = 20, search: str = None) -> Any:
        """Get cached user events list with pagination and search."""
        key = self.keys.user_events_list(user_id, page, page_size, search)
        return self.cache.get(key)

    def cache_user_events(self, user_id: int, events_data: Dict[str, Any], 
                         page: int = 1, page_size: int = 20, search: str = None, timeout: int = 300) -> bool:
        """
        Cache user events list with shorter TTL.
        
        Default: 5 minutes (event lists change when events are created/updated)
        """
        key = self.keys.user_events_list(user_id, page, page_size, search)
        success = self.cache.set(key, events_data, timeout)
        if success:
            logger.debug(f'Cached user events: {user_id} (page: {page}, search: {search})')
        return success

    def invalidate_user_events_lists(self, user_id: int) -> int:
        """Invalidate all cached events lists for a user (all pagination/search combinations)."""
        pattern = f'{self.keys.USER_PREFIX}:{user_id}:events:*'
        count = self.cache.delete_pattern(pattern)
        logger.debug(f'Invalidated {count} user events cache entries for user {user_id}')
        return count

    # User Events Count Caching
    def get_cached_user_events_count(self, user_id: int) -> Any:
        """Get cached user events count."""
        key = self.keys.user_events_count(user_id)
        return self.cache.get(key)

    def cache_user_events_count(self, user_id: int, count: int, timeout: int = 600) -> bool:
        """
        Cache user events count.
        
        Default: 10 minutes (total counts change less frequently)
        """
        key = self.keys.user_events_count(user_id)
        success = self.cache.set(key, count, timeout)
        if success:
            logger.debug(f'Cached user events count: {user_id} = {count}')
        return success

    def invalidate_user_events_count(self, user_id: int) -> bool:
        """Invalidate cached user events count."""
        key = self.keys.user_events_count(user_id)
        return self.cache.delete(key)

    # User Recent Events Caching
    def get_cached_user_recent_events(self, user_id: int, limit: int = 5) -> Any:
        """Get cached user recent events."""
        key = self.keys.user_recent_events(user_id, limit)
        return self.cache.get(key)

    def cache_user_recent_events(self, user_id: int, events: List[Any], limit: int = 5, timeout: int = 180) -> bool:
        """
        Cache user recent events.
        
        Default: 3 minutes (recent events change frequently)
        """
        key = self.keys.user_recent_events(user_id, limit)
        success = self.cache.set(key, events, timeout)
        if success:
            logger.debug(f'Cached user recent events: {user_id} (limit: {limit})')
        return success

    def invalidate_user_recent_events(self, user_id: int) -> int:
        """Invalidate all cached recent events for a user (all limits)."""
        pattern = f'{self.keys.USER_PREFIX}:{user_id}:events:recent:*'
        count = self.cache.delete_pattern(pattern)
        logger.debug(f'Invalidated {count} user recent events cache entries for user {user_id}')
        return count

    # Bulk User Operations  
    def invalidate_user_cache(self, user_id: int, cache_types: List[str] = None) -> int:
        """
        Invalidate specific types of user cache or all user cache.
        
        Args:
            user_id: User ID
            cache_types: List of cache types to invalidate (e.g., ['profile', 'events'])
                        If None, invalidates all cache for this user
        
        Returns:
            Number of cache entries deleted
        """
        try:
            if cache_types:
                deleted = 0
                for cache_type in cache_types:
                    if cache_type == 'profile':
                        if self.invalidate_user_profile(user_id):
                            deleted += 1
                    elif cache_type == 'events':
                        deleted += self.invalidate_user_events_lists(user_id)
                        deleted += self.invalidate_user_recent_events(user_id)
                        if self.invalidate_user_events_count(user_id):
                            deleted += 1
                    else:
                        pattern = f'{self.keys.USER_PREFIX}:{user_id}:{cache_type}:*'
                        deleted += self.cache.delete_pattern(pattern)
            else:
                pattern = self.keys.user_pattern(user_id)
                deleted = self.cache.delete_pattern(pattern)

            logger.info(f'Invalidated user cache for user {user_id}: {deleted} keys (types: {cache_types})')
            return deleted

        except Exception as e:
            logger.exception(f'Error invalidating user cache for user {user_id}: {e}')
            return 0

    # Read-Through Pattern Support
    def get_or_set_user_profile(self, user_id: int, fetch_func, timeout: int = 900) -> Any:

        cached_data = self.get_cached_user_profile(user_id)
        if cached_data is not None:
            return cached_data

        try:
            fresh_data = fetch_func()
            if fresh_data is not None:
                self.cache_user_profile(user_id, fresh_data, timeout)
            return fresh_data
        except Exception as e:
            logger.exception(f'Error in get_or_set_user_profile for user {user_id}: {e}')
            return None

    def get_or_set_user_events(self, user_id: int, fetch_func, page: int = 1, 
                              page_size: int = 20, search: str = None, timeout: int = 300) -> Any:
        """
        Get user events from cache, or fetch and cache if not found.
        
        Args:
            user_id: User ID
            fetch_func: Function to call if cache miss (should return events data)
            page: Page number for pagination
            page_size: Items per page
            search: Search query
            timeout: Cache TTL in seconds
        
        Returns:
            User events data from cache or freshly fetched
        """
        cached_data = self.get_cached_user_events(user_id, page, page_size, search)
        if cached_data is not None:
            return cached_data

        try:
            fresh_data = fetch_func()
            if fresh_data is not None:
                self.cache_user_events(user_id, fresh_data, page, page_size, search, timeout)
            return fresh_data
        except Exception as e:
            logger.exception(f'Error in get_or_set_user_events for user {user_id}: {e}')
            return None


# Module-level singleton for shared use
user_cache_service = UserCacheService()
