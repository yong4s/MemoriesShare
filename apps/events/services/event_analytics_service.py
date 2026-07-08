"""Event analytics: cached statistics for the events domain only."""

import logging
from typing import Any

from apps.events.cache.event_cache_service import event_cache_service
from apps.events.cache.event_cache_service import EventCacheService
from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.dal.event_dal import EventDAL

logger = logging.getLogger(__name__)


class EventAnalyticsService:
    def __init__(
        self,
        analytics_dal: EventAnalyticsDAL | None = None,
        cache_service: EventCacheService | None = None,
        event_dal: EventDAL | None = None,
    ):
        self.dal = analytics_dal or EventAnalyticsDAL()
        self.cache_service = cache_service or event_cache_service
        self.event_dal = event_dal or EventDAL()

    def get_event_statistics(self, event) -> dict[str, Any]:
        """Cached participant counts by role/RSVP (5-min TTL)."""
        return (
            self.cache_service.get_or_set_event_statistics(
                event_uuid=str(event.event_uuid),
                fetch_func=lambda: self.dal.get_event_statistics(event),
                timeout=300,
            )
            or {}
        )

    def get_user_event_analytics(self, user_id: int) -> dict[str, Any]:
        return {
            'user_statistics': self.dal.get_user_participation_statistics(user_id),
            'recent_events': self.event_dal.get_recent_events(user_id, limit=5),
            'upcoming_events': self.event_dal.get_upcoming_events(user_id, limit=5),
        }


# Module-level singleton for shared use
event_analytics_service = EventAnalyticsService()
