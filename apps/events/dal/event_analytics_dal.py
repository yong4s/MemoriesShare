"""
Event Analytics Data Access Layer - Focused on Event Statistics Only

Handles database operations only for event analytics and statistics.
Follows single responsibility principle for loose coupling.
"""

from typing import Any

from django.db.models import Count
from django.db.models import Q

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant


class EventAnalyticsDAL:
    """Data Access Layer for event analytics and statistics only.

    Event-domain queryset reads (recent/upcoming/count by user) live on
    EventDAL; this class is dedicated to aggregations and per-user
    participation analytics.
    """

    def get_event_statistics(self, event: Event) -> dict[str, Any]:
        """Get detailed statistics for event"""
        participants = EventParticipant.objects.filter(event=event)

        return participants.aggregate(
            total_participants=Count('id'),
            accepted_count=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.ACCEPTED)),
            pending_count=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.PENDING)),
            declined_count=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.DECLINED)),
            owners_count=Count('id', filter=Q(role=EventParticipant.Role.OWNER)),
            moderators_count=Count('id', filter=Q(role=EventParticipant.Role.MODERATOR)),
            guests_count=Count('id', filter=Q(role=EventParticipant.Role.GUEST)),
        )

    def get_user_participation_statistics(self, user_id: int) -> dict[str, Any]:
        """Get user's event participation statistics"""
        user_participations = EventParticipant.objects.filter(user_id=user_id)

        return user_participations.aggregate(
            total_events=Count('event', distinct=True),
            owned_events=Count('event', filter=Q(role=EventParticipant.Role.OWNER), distinct=True),
            moderated_events=Count('event', filter=Q(role=EventParticipant.Role.MODERATOR), distinct=True),
            guest_events=Count('event', filter=Q(role=EventParticipant.Role.GUEST), distinct=True),
            accepted_events=Count('event', filter=Q(rsvp_status=EventParticipant.RsvpStatus.ACCEPTED), distinct=True),
            pending_events=Count('event', filter=Q(rsvp_status=EventParticipant.RsvpStatus.PENDING), distinct=True),
        )
