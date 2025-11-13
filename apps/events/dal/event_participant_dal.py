"""
Event Participant Data Access Layer - Focused on EventParticipant Model Only

Handles database operations only for the EventParticipant model.
Follows single responsibility principle for loose coupling.
"""

from typing import Any, Dict, List
from django.db.models import Q

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.cache.cache_decorators import cached_method


class EventParticipantDAL:
    """Data Access Layer for EventParticipant model operations only"""

    def create_participant(self, participation_data: dict[str, Any]) -> EventParticipant:
        """Create new participant"""
        return EventParticipant.objects.create(**participation_data)

    def get_user_participation(self, event: Event, user) -> EventParticipant | None:
        """Get user's participation in event"""
        try:
            return EventParticipant.objects.get(event=event, user=user)
        except EventParticipant.DoesNotExist:
            return None

    def get_user_participation_by_id(self, event: Event, user_id: int) -> EventParticipant | None:
        """Get user's participation by user ID"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None

    def is_user_participant(self, event: Event, user) -> bool:
        """Check if user is participant in event"""
        return EventParticipant.objects.filter(event=event, user=user).exists()

    def is_user_participant_by_id(self, event: Event, user_id: int) -> bool:
        """Check if user is participant by user ID"""
        return EventParticipant.objects.filter(event=event, user_id=user_id).exists()

    def get_event_participants(
        self, event: Event, role_filter: str | None = None, rsvp_filter: str | None = None
    ) -> list[EventParticipant]:
        """Get event participants with optional filters"""
        queryset = EventParticipant.objects.filter(event=event).select_related('user')

        if role_filter:
            queryset = queryset.filter(role=role_filter)

        if rsvp_filter:
            queryset = queryset.filter(rsvp_status=rsvp_filter)

        return list(queryset.order_by('created_at'))

    def update_participant_rsvp(self, participation: EventParticipant, rsvp_status: str) -> EventParticipant:
        """Update participant RSVP status"""
        participation.rsvp_status = rsvp_status
        participation.save(update_fields=['rsvp_status', 'updated_at'])
        return participation

    def remove_participant(self, participation: EventParticipant) -> bool:
        """Remove participant from event"""
        participation.delete()
        return True

    @cached_method(timeout=300)  # 5 minutes cache for participant count
    def get_participants_count(self, event: Event) -> int:
        """Get total participants count for event"""
        return EventParticipant.objects.filter(event=event).count()

    def get_participants_by_role(self, event: Event, role: str) -> list[EventParticipant]:
        """Get participants by role"""
        return list(
            EventParticipant.objects.filter(event=event, role=role)
            .select_related('user')
            .order_by('created_at')
        )

    def get_participants_by_rsvp(self, event: Event, rsvp_status: str) -> list[EventParticipant]:
        """Get participants by RSVP status"""
        return list(
            EventParticipant.objects.filter(event=event, rsvp_status=rsvp_status)
            .select_related('user')
            .order_by('created_at')
        )

    def get_user_events_as_participant(self, user_id: int) -> list[Event]:
        """Get events where user is a participant"""
        return list(
            Event.objects.filter(eventparticipant__user_id=user_id)
            .distinct()
            .select_related('user')
            .order_by('-created_at')
        )