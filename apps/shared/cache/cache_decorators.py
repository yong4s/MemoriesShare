"""
Cache Decorators for Method-Level Caching

Provides decorators for automatic caching and cache invalidation
with consistent key generation and error handling.
"""

import functools
import hashlib
import logging
from typing import Any, Callable, List, Optional, Union

from .cache_manager import CacheManager
from .cache_keys import CacheKeys


logger = logging.getLogger(__name__)


def cached_method(
    key_func: Optional[Callable] = None,
    timeout: int = 300,
    cache_manager: Optional[CacheManager] = None
):
    """
    Decorator for caching method results with automatic key generation.
    
    Args:
        key_func: Function to generate cache key from method args (optional)
        timeout: Cache TTL in seconds (default: 5 minutes)
        cache_manager: CacheManager instance (default: creates new)
        
    Example:
        @cached_method(timeout=600)
        def get_user_profile(self, user_id):
            return self.dal.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get or create cache manager
            cache = cache_manager or CacheManager()
            
            try:
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation based on function name and args
                    instance = args[0] if args else None
                    class_name = instance.__class__.__name__ if instance else 'function'
                    
                    # Create hash from args/kwargs for consistent keys
                    args_str = str(args[1:]) + str(sorted(kwargs.items()))
                    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                    
                    cache_key = f"{class_name}:{func.__name__}:{args_hash}"
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cached result for {func.__name__}: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator error for {func.__name__}: {e}")
                # Fallback to function execution without cache
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def cache_user_data(
    timeout: int = 900,  # 15 minutes
    key_type: str = 'profile'
):
    """
    Specialized decorator for caching user-related data.
    
    Args:
        timeout: Cache TTL in seconds (default: 15 minutes)
        key_type: Type of user data being cached (for key generation)
        
    Example:
        @cache_user_data(timeout=1800, key_type='preferences')
        def get_user_preferences(self, user_id):
            return self.dal.get_user_preferences(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheManager()
            
            try:
                # Extract user_id from arguments
                user_id = None
                if args and len(args) > 1:
                    user_id = args[1]  # self, user_id, ...
                elif 'user_id' in kwargs:
                    user_id = kwargs['user_id']
                
                if user_id is None:
                    logger.warning(f"Could not extract user_id for {func.__name__}, skipping cache")
                    return func(*args, **kwargs)
                
                # Generate user-specific cache key
                cache_key = f"{CacheKeys.USER_PREFIX}:{user_id}:{key_type}"
                
                # Try cache first
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute and cache
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                
                return result
                
            except Exception as e:
                logger.error(f"User cache decorator error for {func.__name__}: {e}")
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def cache_event_data(
    timeout: int = 600,  # 10 minutes
    key_type: str = 'detail'
):
    """
    Specialized decorator for caching event-related data.
    
    Args:
        timeout: Cache TTL in seconds (default: 10 minutes)
        key_type: Type of event data being cached
        
    Example:
        @cache_event_data(timeout=300, key_type='participants')
        def get_event_participants(self, event_uuid):
            return self.dal.get_participants(event_uuid)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheManager()
            
            try:
                # Extract event_uuid from arguments
                event_uuid = None
                if args and len(args) > 1:
                    event_uuid = args[1]  # self, event_uuid, ...
                elif 'event_uuid' in kwargs:
                    event_uuid = kwargs['event_uuid']
                
                if event_uuid is None:
                    logger.warning(f"Could not extract event_uuid for {func.__name__}, skipping cache")
                    return func(*args, **kwargs)
                
                # Generate event-specific cache key
                cache_key = f"{CacheKeys.EVENT_PREFIX}:{event_uuid}:{key_type}"
                
                # Try cache first
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute and cache
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                
                return result
                
            except Exception as e:
                logger.error(f"Event cache decorator error for {func.__name__}: {e}")
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def invalidate_cache_after(
    patterns: Union[str, List[str]],
    cache_manager: Optional[CacheManager] = None
):
    """
    Decorator to invalidate cache patterns after method execution.
    
    Args:
        patterns: Cache pattern(s) to invalidate
        cache_manager: CacheManager instance (default: creates new)
        
    Example:
        @invalidate_cache_after(['user:*:events:*'])
        def create_event(self, user_id, event_data):
            return self.dal.create_event(event_data)
    """
    if isinstance(patterns, str):
        patterns = [patterns]
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_manager or CacheManager()
            
            try:
                # Execute function first
                result = func(*args, **kwargs)
                
                # Invalidate cache patterns after successful execution
                for pattern in patterns:
                    # Replace placeholders with actual values from args/kwargs
                    resolved_pattern = pattern
                    
                    # Simple placeholder replacement
                    if '{user_id}' in pattern and args and len(args) > 1:
                        resolved_pattern = pattern.replace('{user_id}', str(args[1]))
                    if '{event_uuid}' in pattern and args and len(args) > 1:
                        resolved_pattern = pattern.replace('{event_uuid}', str(args[1]))
                        
                    deleted_count = cache.delete_pattern(resolved_pattern)
                    logger.info(f"Invalidated {deleted_count} cache entries with pattern: {resolved_pattern}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache invalidation error for {func.__name__}: {e}")
                # Still return the function result even if cache invalidation fails
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def invalidate_user_cache_after(
    user_id_param: str = 'user_id',
    cache_types: Optional[List[str]] = None
):
    """
    Decorator to invalidate user cache after method execution.
    
    Args:
        user_id_param: Parameter name containing user ID
        cache_types: Specific cache types to invalidate (None for all)
        
    Example:
        @invalidate_user_cache_after(cache_types=['events', 'profile'])
        def update_user(self, user_id, data):
            return self.dal.update_user(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheManager()
            
            try:
                # Execute function first
                result = func(*args, **kwargs)
                
                # Extract user_id
                user_id = None
                if user_id_param in kwargs:
                    user_id = kwargs[user_id_param]
                elif args and len(args) > 1:
                    user_id = args[1]  # Assume second argument is user_id
                
                if user_id:
                    cache.invalidate_user_cache(user_id, cache_types)
                else:
                    logger.warning(f"Could not extract {user_id_param} for cache invalidation in {func.__name__}")
                
                return result
                
            except Exception as e:
                logger.error(f"User cache invalidation error for {func.__name__}: {e}")
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


def invalidate_event_cache_after(
    event_uuid_param: str = 'event_uuid',
    cache_types: Optional[List[str]] = None
):
    """
    Decorator to invalidate event cache after method execution.
    
    Args:
        event_uuid_param: Parameter name containing event UUID
        cache_types: Specific cache types to invalidate (None for all)
        
    Example:
        @invalidate_event_cache_after(cache_types=['detail', 'participants'])
        def update_event(self, event_uuid, data):
            return self.dal.update_event(event_uuid, data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheManager()
            
            try:
                # Execute function first
                result = func(*args, **kwargs)
                
                # Extract event_uuid
                event_uuid = None
                if event_uuid_param in kwargs:
                    event_uuid = kwargs[event_uuid_param]
                elif args and len(args) > 1:
                    event_uuid = args[1]  # Assume second argument is event_uuid
                
                if event_uuid:
                    cache.invalidate_event_cache(str(event_uuid), cache_types)
                else:
                    logger.warning(f"Could not extract {event_uuid_param} for cache invalidation in {func.__name__}")
                
                return result
                
            except Exception as e:
                logger.error(f"Event cache invalidation error for {func.__name__}: {e}")
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


# Convenience aliases for common use cases
cache_for_5_minutes = functools.partial(cached_method, timeout=300)
cache_for_15_minutes = functools.partial(cached_method, timeout=900)
cache_for_1_hour = functools.partial(cached_method, timeout=3600)