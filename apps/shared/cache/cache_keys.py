"""
Cache Keys Management

Centralized cache key generation with namespace isolation and consistent formatting.
All cache keys follow the pattern: {namespace}:{id}:{type}:{params}
"""

import hashlib
from typing import Optional


class CacheKeys:
    """Centralized cache key generation for consistent namespace isolation"""

    # Cache key prefixes for namespacing
    USER_PREFIX = 'user'
    EVENT_PREFIX = 'event'
    MEDIA_PREFIX = 'media'
    ALBUM_PREFIX = 'album'

    @classmethod
    def user_profile(cls, user_id: int) -> str:
        """Cache key for user profile data

        Args:
            user_id: User ID

        Returns:
            str: Cache key like 'user:123:profile'
        """
        return f'{cls.USER_PREFIX}:{user_id}:profile'

    @classmethod
    def user_events_list(cls, user_id: int, page: int = 1, page_size: int = 20, search: str | None = None) -> str:
        """Cache key for user's events list with pagination and search

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            search: Search query (optional)

        Returns:
            str: Cache key like 'user:123:events:list:1:20:search_hash'
        """
        search_hash = ''
        if search:
            search_hash = hashlib.md5(search.encode()).hexdigest()[:8]

        return f'{cls.USER_PREFIX}:{user_id}:events:list:{page}:{page_size}:{search_hash}'

    @classmethod
    def user_events_count(cls, user_id: int) -> str:
        """Cache key for user's total events count

        Args:
            user_id: User ID

        Returns:
            str: Cache key like 'user:123:events:count'
        """
        return f'{cls.USER_PREFIX}:{user_id}:events:count'

    @classmethod
    def user_recent_events(cls, user_id: int, limit: int = 5) -> str:
        """Cache key for user's recent events

        Args:
            user_id: User ID
            limit: Number of recent events

        Returns:
            str: Cache key like 'user:123:events:recent:5'
        """
        return f'{cls.USER_PREFIX}:{user_id}:events:recent:{limit}'

    @classmethod
    def event_detail(cls, event_uuid: str) -> str:
        """Cache key for event detail with statistics

        Args:
            event_uuid: Event UUID

        Returns:
            str: Cache key like 'event:abc-123:detail'
        """
        return f'{cls.EVENT_PREFIX}:{event_uuid}:detail'

    @classmethod
    def event_statistics(cls, event_uuid: str) -> str:
        """Cache key for event participant statistics

        Args:
            event_uuid: Event UUID

        Returns:
            str: Cache key like 'event:abc-123:stats'
        """
        return f'{cls.EVENT_PREFIX}:{event_uuid}:stats'

    @classmethod
    def event_participants(
        cls,
        event_uuid: str,
        role_filter: str | None = None,
        rsvp_filter: str | None = None,
    ) -> str:
        """Cache key for event participants with optional filters

        Args:
            event_uuid: Event UUID
            role_filter: Optional role filter
            rsvp_filter: Optional RSVP status filter

        Returns:
            str: Cache key like 'event:abc-123:participants:GUEST:ATTENDING'
        """
        filters = []
        if role_filter:
            filters.append(role_filter)
        if rsvp_filter:
            filters.append(rsvp_filter)

        filter_str = ':'.join(filters) if filters else 'all'
        return f'{cls.EVENT_PREFIX}:{event_uuid}:participants:{filter_str}'

    @classmethod
    def event_participant_detail(cls, event_uuid: str, participant_id: int) -> str:
        """Cache key for specific participant detail

        Args:
            event_uuid: Event UUID
            participant_id: Participant ID

        Returns:
            str: Cache key like 'event:abc-123:participant:456'
        """
        return f'{cls.EVENT_PREFIX}:{event_uuid}:participant:{participant_id}'

    # ── Media File Keys ────────────────────────────────────────────────────

    @classmethod
    def media_file_detail(cls, file_uuid: str) -> str:
        """Cache key for media file detail

        Args:
            file_uuid: File UUID

        Returns:
            str: Cache key like 'media:abc-123:detail'
        """
        return f'{cls.MEDIA_PREFIX}:{file_uuid}:detail'

    @classmethod
    def media_event_files(cls, event_uuid: str) -> str:
        """Cache key for all media files in an event

        Args:
            event_uuid: Event UUID

        Returns:
            str: Cache key like 'media:event:abc-123:files'
        """
        return f'{cls.MEDIA_PREFIX}:event:{event_uuid}:files'

    @classmethod
    def media_pattern(cls, identifier: str) -> str:
        """Pattern to match media-related cache keys

        Args:
            identifier: UUID or prefix to match

        Returns:
            str: Pattern like 'media:abc-123:*'
        """
        return f'{cls.MEDIA_PREFIX}:{identifier}:*'

    # ── Album Keys ─────────────────────────────────────────────────────────

    @classmethod
    def album_detail(cls, album_uuid: str) -> str:
        """Cache key for album detail

        Args:
            album_uuid: Album UUID

        Returns:
            str: Cache key like 'album:abc-123:detail'
        """
        return f'{cls.ALBUM_PREFIX}:{album_uuid}:detail'

    @classmethod
    def album_event_list(cls, event_uuid: str) -> str:
        """Cache key for all albums in an event

        Args:
            event_uuid: Event UUID

        Returns:
            str: Cache key like 'album:event:abc-123:list'
        """
        return f'{cls.ALBUM_PREFIX}:event:{event_uuid}:list'

    @classmethod
    def album_event_pattern(cls, event_uuid: str) -> str:
        """Pattern for every album-scoped cache entry associated with an event."""
        return f'{cls.ALBUM_PREFIX}:event:{event_uuid}:*'

    @classmethod
    def album_pattern(cls, identifier: str) -> str:
        """Pattern to match album-related cache keys

        Args:
            identifier: UUID or prefix to match

        Returns:
            str: Pattern like 'album:abc-123:*'
        """
        return f'{cls.ALBUM_PREFIX}:{identifier}:*'

    # Pattern generators for bulk operations
    @classmethod
    def user_pattern(cls, user_id: int) -> str:
        """Pattern to match all user-related cache keys

        Args:
            user_id: User ID

        Returns:
            str: Pattern like 'user:123:*'
        """
        return f'{cls.USER_PREFIX}:{user_id}:*'

    @classmethod
    def event_pattern(cls, event_uuid: str) -> str:
        """Pattern to match all event-related cache keys

        Args:
            event_uuid: Event UUID

        Returns:
            str: Pattern like 'event:abc-123:*'
        """
        return f'{cls.EVENT_PREFIX}:{event_uuid}:*'

    @classmethod
    def user_events_pattern(cls, user_id: int) -> str:
        """Pattern to match all user's event list cache keys

        Args:
            user_id: User ID

        Returns:
            str: Pattern like 'user:123:events:*'
        """
        return f'{cls.USER_PREFIX}:{user_id}:events:*'

    @classmethod
    def validate_key(cls, key: str) -> bool:
        """Validate cache key format

        Args:
            key: Cache key to validate

        Returns:
            bool: True if key format is valid
        """
        parts = key.split(':')
        if len(parts) < 3:
            return False

        namespace = parts[0]
        return namespace in {
            cls.USER_PREFIX,
            cls.EVENT_PREFIX,
            cls.MEDIA_PREFIX,
            cls.ALBUM_PREFIX,
        }
