"""Cache invalidation collaborator for event-domain services.

Centralises the post-commit fan-out that ``EventService``,
``EventParticipantService`` and ``InviteLinkService`` previously each implemented
on their own. One scheduling call → one ``transaction.on_commit`` callback that
clears event-domain keys and the affected users' list caches.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.accounts.cache.user_cache_service import UserCacheService
    from apps.events.cache.event_cache_service import EventCacheService

logger = logging.getLogger(__name__)


class EventCacheInvalidator:
    """Schedule transactional cache invalidation for an event + affected users."""

    def __init__(self, event_cache: EventCacheService, user_cache: UserCacheService) -> None:
        self.event_cache = event_cache
        self.user_cache = user_cache

    def invalidate(
        self,
        event_uuid: object,
        user_ids: Iterable[int | None],
        scope: list[str],
    ) -> None:
        """Register a post-commit callback that clears the relevant cache keys.

        Args:
            event_uuid: UUID-like; coerced to str for cache keys.
            user_ids: User IDs whose ``events`` list caches should be busted.
                ``None`` entries are ignored, duplicates collapse to one bust.
            scope: Event-domain key types to invalidate
                (e.g. ``['detail', 'participants', 'statistics']``).
        """
        event_uuid_str = str(event_uuid)
        unique_user_ids = {uid for uid in user_ids if uid is not None}
        scope_tuple = tuple(scope)

        def _run() -> None:
            try:
                if scope_tuple:
                    self.event_cache.invalidate_event_cache(event_uuid_str, list(scope_tuple))
                for uid in unique_user_ids:
                    self.user_cache.invalidate_user_events_lists(uid)
            except Exception:
                logger.warning(
                    'Cache invalidation failed for event %s users %s',
                    event_uuid_str,
                    unique_user_ids,
                    exc_info=True,
                )

        transaction.on_commit(_run)
