from typing import Any, Dict, List
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError

from apps.events.models.event import Event
from apps.events.exceptions import EventNotFoundError, EventCreationError
from apps.shared.exceptions import ServiceUnavailableError, ValidationError
import logging

logger = logging.getLogger(__name__)


class EventDAL:
    """Data Access Layer for Event model operations only"""

    def create_event(self, event_data: dict[str, Any]) -> Event:
        """Create new event with exception translation"""
        try:
            return Event.objects.create(**event_data)
        except (IntegrityError, DjangoValidationError) as e:
            logger.error(f"Event creation failed - validation/integrity error: {e}")
            raise ValidationError(f"Event creation failed: {str(e)}")
        except DatabaseError as e:
            logger.error(f"Event creation failed - database error: {e}")
            raise ServiceUnavailableError(f"Database service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Event creation failed - unexpected error: {e}")
            raise EventCreationError(f"Unexpected error during event creation: {str(e)}")

    def get_event_by_uuid(self, event_uuid: str) -> Event:
        """Get event by UUID with exception translation"""
        try:
            return Event.objects.get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            logger.debug(f"Event not found: {event_uuid}")
            raise EventNotFoundError(event_identifier=event_uuid)
        except DatabaseError as e:
            logger.error(f"Database error while fetching event {event_uuid}: {e}")
            raise ServiceUnavailableError(f"Database service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching event {event_uuid}: {e}")
            raise ServiceUnavailableError(f"Unexpected database error: {str(e)}")

    def get_event_by_uuid_optimized(self, event_uuid: str) -> Event:
        """Get event with optimized queries and exception translation"""
        try:
            return Event.objects.select_related().prefetch_related(
                'participants_through__user'
            ).get(event_uuid=event_uuid)
        except Event.DoesNotExist:
            logger.debug(f"Event not found (optimized query): {event_uuid}")
            raise EventNotFoundError(event_identifier=event_uuid)
        except DatabaseError as e:
            logger.error(f"Database error in optimized event query {event_uuid}: {e}")
            raise ServiceUnavailableError(f"Database service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in optimized event query {event_uuid}: {e}")
            raise ServiceUnavailableError(f"Unexpected database error: {str(e)}")

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
                participants_through__user_id=user_id,
                participants_through__role=EventParticipant.Role.OWNER
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
        """Update event fields with exception translation"""
        try:
            for field, value in validated_data.items():
                setattr(event, field, value)
            event.save()
            return event
        except (IntegrityError, DjangoValidationError) as e:
            logger.error(f"Event update failed - validation error: {e}")
            raise ValidationError(f"Event update validation failed: {str(e)}")
        except DatabaseError as e:
            logger.error(f"Event update failed - database error: {e}")
            raise ServiceUnavailableError(f"Database service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Event update failed - unexpected error: {e}")
            raise ServiceUnavailableError(f"Unexpected error during event update: {str(e)}")

    def delete_event(self, event: Event) -> bool:
        """Delete event with exception translation"""
        try:
            event.delete()
            return True
        except IntegrityError as e:
            logger.error(f"Event deletion failed - integrity constraint: {e}")
            raise ValidationError(f"Cannot delete event due to existing references: {str(e)}")
        except DatabaseError as e:
            logger.error(f"Event deletion failed - database error: {e}")
            raise ServiceUnavailableError(f"Database service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Event deletion failed - unexpected error: {e}")
            raise ServiceUnavailableError(f"Unexpected error during event deletion: {str(e)}")

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
