"""
Event Analytics Service - Event Domain Only

Provides cached analytics and statistics ONLY for events domain.
User-specific analytics moved to Users domain to maintain proper separation.
"""

import logging
from typing import Any
from typing import Dict

from apps.events.cache.event_cache_service import event_cache_service
from apps.events.cache.event_cache_service import EventCacheService
from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.dal.event_dal import EventDAL
from apps.events.exceptions import EventNotFoundError

logger = logging.getLogger(__name__)


class EventAnalyticsService:
    """
    High-performance analytics service for Events domain only.

    Responsibilities:
    - Caching heavy EVENT analytics queries (COUNT, GROUP BY aggregations)
    - Read-Through pattern for event analytics data
    - Event-specific cache invalidation
    - Performance optimization for event dashboard queries

    DOMAIN SEPARATION: Only handles Event domain analytics.
    User analytics moved to Users domain.
    """

    def __init__(
        self,
        analytics_dal: EventAnalyticsDAL = None,
        cache_service: EventCacheService = None,
        event_dal: EventDAL = None,
    ):
        self.dal = analytics_dal or EventAnalyticsDAL()
        self.cache_service = cache_service or event_cache_service
        self.event_dal = event_dal or EventDAL()

    def get_event_statistics(self, event) -> dict[str, Any]:
        """
        Get event statistics with caching.

        Heavy query with COUNT and GROUP BY operations.
        Cache TTL: 5 minutes (statistics change when participants join/leave)

        Args:
            event: Event instance

        Returns:
            Dictionary with participant counts by role and RSVP status
        """

        def fetch_stats():
            return self.dal.get_event_statistics(event)

        # Use Read-Through pattern with 5-minute cache
        return (
            self.cache_service.get_or_set_event_statistics(
                event_uuid=str(event.event_uuid),
                fetch_func=fetch_stats,
                timeout=300,  # 5 minutes
            )
            or {}
        )

    def get_event_analytics_summary(self, event_uuid: str) -> dict[str, Any]:
        """
        Get comprehensive analytics summary for an event.

        Combines multiple analytics queries with intelligent caching.
        Cache TTL: 5 minutes

        Args:
            event_uuid: Event UUID

        Returns:
            Comprehensive analytics summary for the event
        """
        cache_key = f'event:{event_uuid}:analytics_summary'

        # Try cache first
        cached_summary = self.cache_service.cache.get(cache_key)
        if cached_summary is not None:
            logger.debug(f'Cache HIT: analytics summary for event {event_uuid}')
            return cached_summary

        # Cache miss - build comprehensive summary
        try:
            logger.debug(f'Cache MISS: building analytics summary for event {event_uuid}')
            event = self.event_dal.get_event_by_uuid_optimized_with_participants(event_uuid)
        except EventNotFoundError:
            logger.info(f'Analytics summary requested for missing event {event_uuid}')
            return {}

        statistics = self.get_event_statistics(event)

        summary = {
            'event_uuid': event_uuid,
            'event_name': event.event_name,
            'statistics': statistics,
            'participant_breakdown': {
                'by_role': {
                    'owners': statistics.get('owners_count', 0),
                    'moderators': statistics.get('moderators_count', 0),
                    'guests': statistics.get('guests_count', 0),
                },
                'by_rsvp': {
                    'accepted': statistics.get('accepted_count', 0),
                    'pending': statistics.get('pending_count', 0),
                    'declined': statistics.get('declined_count', 0),
                },
            },
            'total_participants': statistics.get('total_participants', 0),
        }

        self.cache_service.cache.set(cache_key, summary, timeout=300)
        return summary

    def warm_event_analytics_cache(self, event_uuid: str) -> None:
        """
        Proactively warm event analytics cache.

        Use this after major operations that affect event analytics.

        Args:
            event_uuid: Event UUID to warm
        """
        try:
            logger.info(f'Warming analytics cache for event {event_uuid}')
            # Trigger cache population
            self.get_event_analytics_summary(event_uuid)

        except Exception as e:
            logger.exception(f'Error warming analytics cache for event {event_uuid}: {e}')


# Module-level singleton for shared use
event_analytics_service = EventAnalyticsService()
