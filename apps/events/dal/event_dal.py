"""
Event Data Access Layer - Focused on Event Model Only

Handles database operations only for the Event model.
Follows single responsibility principle for loose coupling.
"""

from typing import Any, Dict, List
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from apps.events.models.event import Event
from apps.shared.cache.cache_decorators import cached_method


class EventDAL:
    """Data Access Layer for Event model operations only"""

    def create_event(self, event_data: dict[str, Any]) -> Event:
        """Create new event"""
        return Event.objects.create(**event_data)

    def get_event_by_uuid(self, event_uuid: str) -> Event | None:
        """Get event by UUID"""
        try:
            return Event.objects.get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            return None

    @cached_method(timeout=300)  # 5 minutes cache for event details  
    def get_event_by_uuid_optimized(self, event_uuid: str) -> Event | None:
        """Get event with optimized queries for related data"""
        try:
            return Event.objects.select_related().prefetch_related(
                'eventparticipant_set__user'
            ).get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            return None

    def get_user_events_paginated(self, user_id: int, filters: dict[str, Any]) -> dict[str, Any]:
        """Get paginated list of user's events"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        search = filters.get('search', '')
        owned_only = filters.get('owned_only', False)

        # Base queryset with statistics
        if owned_only:
            # Get events where user is OWNER in EventParticipant
            from apps.events.models.event_participant import EventParticipant
            queryset = Event.objects.filter(
                eventparticipant__user_id=user_id,
                eventparticipant__role=EventParticipant.Role.OWNER
            ).distinct()
        else:
            queryset = Event.objects.for_user(user_id)

        queryset = queryset.with_statistics().order_by('-created_at')

        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(event_name__icontains=search) | Q(description__icontains=search)
            )

        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            'events': list(page_obj),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
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

    def get_events_with_statistics(self, event_ids: List[int]):
        """Get events with statistics for multiple IDs"""
        return Event.objects.filter(id__in=event_ids).with_statistics().select_related('user')

    def get_user_events_count(self, user_id: int) -> int:
        """Get total events count for user"""
        return Event.objects.for_user(user_id).count()

    def get_recent_events(self, user_id: int, limit: int = 5) -> List[Event]:
        """Get recent events for user"""
        return list(Event.objects.for_user(user_id).order_by('-created_at')[:limit])

    def get_upcoming_events(self, user_id: int, limit: int = 5) -> List[Event]:
        """Get upcoming events for user"""
        return list(
            Event.objects.for_user(user_id)
            .filter(date__gte=timezone.now().date())
            .order_by('date')[:limit]
        )