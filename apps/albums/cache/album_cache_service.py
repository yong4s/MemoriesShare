"""Domain-specific cache service for Albums.

Mirrors the EventCacheService pattern: all album-related cache reads, writes,
and invalidations flow through this service so the model layer stays free of
cache concerns and transaction.on_commit hooks own invalidation.
"""

from __future__ import annotations

import logging

from apps.shared.cache.base_cache_client import base_cache_client
from apps.shared.cache.base_cache_client import BaseCacheClient
from apps.shared.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class AlbumCacheService:
    """Cache operations for album file counts, type summaries, and invalidation."""

    def __init__(self, cache_client: BaseCacheClient | None = None) -> None:
        self.cache = cache_client or base_cache_client
        self.keys = CacheKeys

    def invalidate_album(self, album_uuid: str) -> int:
        """Invalidate every cache entry scoped to a single album."""
        pattern = self.keys.album_pattern(album_uuid)
        deleted = self.cache.delete_pattern(pattern)
        logger.debug('Invalidated %s album cache keys for %s', deleted, album_uuid)
        return deleted

    def invalidate_event_albums(self, event_uuid: str) -> int:
        """Invalidate album listings scoped to an event."""
        pattern = self.keys.album_event_pattern(event_uuid)
        deleted = self.cache.delete_pattern(pattern)
        logger.debug('Invalidated %s album-event cache keys for %s', deleted, event_uuid)
        return deleted


album_cache_service = AlbumCacheService()
