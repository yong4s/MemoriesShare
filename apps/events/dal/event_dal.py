from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from apps.events.models.event import Event
from apps.shared.decorators.database import handle_db_errors


class EventDAL:
    """Data Access Layer for Event model operations only"""

    @handle_db_errors(operation_type="create", model_name="Event")
    def create_event(self, event_data: dict[str, Any]) -> Event:
        """Create new event"""
        return Event.objects.create(**event_data)

    @handle_db_errors(operation_type="read", model_name="Event")
    def get_event_by_uuid(self, event_uuid: str) -> Event:
        """Get event by UUID"""
        return Event.objects.get(event_uuid=event_uuid)

    @handle_db_errors(operation_type="read", model_name="Event")
    def get_event_by_uuid_optimized(self, event_uuid: str) -> Event:
        """Get event with optimized queries"""
        return Event.objects.optimized().get(event_uuid=event_uuid)

    def get_owned_events_queryset(self, user_id: int) -> QuerySet[Event]:
        """Get queryset of events where user is owner"""
        return Event.objects.for_owner(user_id)

    def get_user_events_queryset(self, user_id: int) -> QuerySet[Event]:
        """Get queryset of all events accessible to user"""
        return Event.objects.accessible_to_user(user_id)

    @handle_db_errors(operation_type="update", model_name="Event")
    def update_event(self, event: Event, validated_data: dict[str, Any]) -> Event:
        """Update event fields"""
        for field, value in validated_data.items():
            setattr(event, field, value)
        event.save()
        return event

    @handle_db_errors(operation_type="delete", model_name="Event")
    def delete_event(self, event: Event) -> bool:
        """Delete event"""
        event.delete()
        return True

    def get_events_with_statistics(self, event_ids: list[int]):
        """Get events with statistics for multiple IDs"""
        return Event.objects.filter(id__in=event_ids).with_statistics_ordered()

    def get_user_events_count(self, user_id: int) -> int:
        """Get total events count for user"""
        return Event.objects.for_user(user_id).count()

    def get_recent_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get recent events for user"""
        return list(Event.objects.for_user(user_id).order_by("-created_at")[:limit])

    def get_upcoming_events(self, user_id: int, limit: int = 5) -> list[Event]:
        """Get upcoming events for user"""
        return list(Event.objects.for_user(user_id).upcoming().order_by("date")[:limit])
