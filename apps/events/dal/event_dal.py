"""
Event Data Access Layer

Handles all database operations for events and participants.
Optimized queries with proper prefetching and annotations.
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant


class EventDAL:
    """Data Access Layer for Event operations"""

    def create_event(self, event_data: dict[str, Any]) -> Event:
        """Create new event"""
        return Event.objects.create(**event_data)

    def get_event_by_uuid(self, event_uuid: str) -> Event | None:
        """Get event by UUID"""
        try:
            return Event.objects.get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            return None

    def get_event_by_uuid_optimized(self, event_uuid: str) -> Event | None:
        """Get event with optimized queries"""
        try:
            return (
                Event.objects.select_related('user')
                .prefetch_related(Prefetch('participants', queryset=EventParticipant.objects.select_related('user')))
                .get(event_uuid=event_uuid)
            )
        except Event.DoesNotExist:
            return None

    def get_user_events_paginated(self, user_id: int, filters: dict[str, Any]) -> dict[str, Any]:
        """Get paginated list of user's events"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        search = filters.get('search', '')

        # Base queryset with statistics
        queryset = Event.objects.for_user(user_id).with_statistics().select_related('user').order_by('-created_at')

        # Apply search filter
        if search:
            queryset = queryset.filter(Q(event_name__icontains=search) | Q(description__icontains=search))

        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            'events': list(page_obj),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_events': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        }

    def update_event(self, event: Event, validated_data: dict[str, Any]) -> Event:
        """Update event fields"""
        for field, value in validated_data.items():
            setattr(event, field, value)
        event.save()
        return event

    def delete_event(self, event: Event) -> bool:
        """Delete event"""
        event.delete()
        return True

    # =============================================================================
    # PARTICIPANT OPERATIONS
    # =============================================================================

    def get_event_participants(
        self, event: Event, role_filter: str | None = None, rsvp_filter: str | None = None
    ) -> list[EventParticipant]:
        """Get event participants with optional filters"""
        queryset = (
            EventParticipant.objects.filter(event=event).select_related('user', 'event').order_by('role', 'created_at')
        )

        if role_filter:
            queryset = queryset.filter(role=role_filter)

        if rsvp_filter:
            queryset = queryset.filter(rsvp_status=rsvp_filter)

        return list(queryset)

    def create_participant(self, participation_data: dict[str, Any]) -> EventParticipant:
        """Create new participant"""
        return EventParticipant.objects.create(**participation_data)

    def get_user_participation(self, event: Event, user_id: int) -> EventParticipant | None:
        """Get user's participation in event"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None

    def get_user_participation_by_id(self, event: Event, user_id: int) -> EventParticipant | None:
        """Get user's participation in event by user ID"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None

    def is_user_participant(self, event: Event, user_id: int) -> bool:
        """Check if user is participant"""
        return EventParticipant.objects.filter(event=event, user_id=user_id).exists()

    def is_user_participant_by_id(self, event: Event, user_id: int) -> bool:
        """Check if user is participant by user ID"""
        return EventParticipant.objects.filter(event=event, user_id=user_id).exists()

    def remove_participant(self, participation: EventParticipant) -> bool:
        """Remove participant"""
        participation.delete()
        return True

    def update_participant_rsvp(self, participation: EventParticipant, rsvp_status: str) -> EventParticipant:
        """Update participant RSVP status"""
        participation.rsvp_status = rsvp_status
        participation.save(update_fields=['rsvp_status'])
        return participation

    # =============================================================================
    # BULK OPERATIONS
    # =============================================================================

    def get_events_with_statistics(self, event_ids: list[int]) -> QuerySet[Event]:
        """Get events with statistics for multiple IDs"""
        return (
            Event.objects.filter(id__in=event_ids)
            .with_statistics()
            .select_related('user')
            .prefetch_related(Prefetch('participants', queryset=EventParticipant.objects.select_related('user')))
        )

    def bulk_update_participant_rsvp(self, participant_ids: list[int], rsvp_status: str) -> int:
        """Bulk update RSVP status for multiple participants"""
        return EventParticipant.objects.filter(id__in=participant_ids).update(rsvp_status=rsvp_status)

    # =============================================================================
    # ANALYTICS QUERIES
    # =============================================================================

    def get_event_statistics(self, event: Event) -> dict[str, Any]:
        """Get comprehensive event statistics"""
        participants_stats = EventParticipant.objects.filter(event=event).aggregate(
            total_participants=Count('id'),
            attending=Count('id', filter=Q(rsvp_status='ATTENDING')),
            not_attending=Count('id', filter=Q(rsvp_status='NOT_ATTENDING')),
            maybe=Count('id', filter=Q(rsvp_status='MAYBE')),
            pending=Count('id', filter=Q(rsvp_status='PENDING')),
            owners=Count('id', filter=Q(role='OWNER')),
            moderators=Count('id', filter=Q(role='MODERATOR')),
            guests=Count('id', filter=Q(role='GUEST')),
        )

        return participants_stats

    def get_user_events_count(self, user_id: int) -> int:
        """Get total events count for user"""
        return Event.objects.for_user(user_id).count()

    def get_recent_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get recent events for user"""
        return list(Event.objects.for_user(user_id).order_by('-created_at')[:limit])

    def get_upcoming_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get upcoming events for user"""
        return list(Event.objects.for_user(user_id).filter(date__gte=timezone.now().date()).order_by('date')[:limit])
