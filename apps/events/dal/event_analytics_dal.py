"""
Event Analytics Data Access Layer - Focused on Event Statistics Only

Handles database operations only for event analytics and statistics.
Follows single responsibility principle for loose coupling.
"""

from typing import Any
from typing import Dict
from typing import List

from django.db.models import Count
from django.db.models import Q
from django.utils import timezone

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant

# Removed cache decorators - using simple direct caching


class EventAnalyticsDAL:
    """Data Access Layer for event analytics and statistics only"""

    def get_events_with_statistics(self, event_ids: list[int]) -> list[Event]:
        """Get events with statistics for multiple IDs"""
        return list(Event.objects.filter(id__in=event_ids).with_statistics().select_related('user'))

    def get_user_events_count(self, user_id: int) -> int:
        """Get total events count for user"""
        return Event.objects.for_user(user_id).count()

    def get_recent_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get recent events for user"""
        return list(Event.objects.for_user(user_id).order_by('-created_at')[:limit])

    def get_upcoming_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get upcoming events for user"""
        return list(Event.objects.for_user(user_id).filter(date__gte=timezone.now().date()).order_by('date')[:limit])

    # Cache removed  # 5 minutes cache for event statistics
    def get_event_statistics(self, event: Event) -> dict[str, Any]:
        """Get detailed statistics for event"""
        participants = EventParticipant.objects.filter(event=event)

        return participants.aggregate(
            total_participants=Count('id'),
            accepted_count=Count('id', filter=Q(rsvp_status='ACCEPTED')),
            pending_count=Count('id', filter=Q(rsvp_status='PENDING')),
            declined_count=Count('id', filter=Q(rsvp_status='DECLINED')),
            owners_count=Count('id', filter=Q(role='OWNER')),
            moderators_count=Count('id', filter=Q(role='MODERATOR')),
            guests_count=Count('id', filter=Q(role='GUEST')),
        )

    # Cache removed  # 10 minutes cache for user statistics
    def get_user_participation_statistics(self, user_id: int) -> dict[str, Any]:
        """Get user's event participation statistics"""
        user_participations = EventParticipant.objects.filter(user_id=user_id)

        return user_participations.aggregate(
            total_events=Count('event', distinct=True),
            owned_events=Count('event', filter=Q(role='OWNER'), distinct=True),
            moderated_events=Count('event', filter=Q(role='MODERATOR'), distinct=True),
            guest_events=Count('event', filter=Q(role='GUEST'), distinct=True),
            accepted_events=Count('event', filter=Q(rsvp_status='ACCEPTED'), distinct=True),
            pending_events=Count('event', filter=Q(rsvp_status='PENDING'), distinct=True),
        )

    def get_events_by_date_range(self, user_id: int, start_date=None, end_date=None) -> list[Event]:
        """Get events for user within date range"""
        queryset = Event.objects.for_user(user_id)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return list(queryset.order_by('date'))

    # Cache removed - 15 minutes cache for popular events
    def get_popular_events(self, limit: int = 10) -> list[Event]:
        """Get events with most participants"""
        return list(
            Event.objects.annotate(participant_count=Count('participants')).order_by('-participant_count')[:limit]
        )
