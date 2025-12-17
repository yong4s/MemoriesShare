"""
Event Participant Data Access Layer - Focused on EventParticipant Model Only

Handles database operations only for the EventParticipant model.
Follows single responsibility principle for loose coupling.
"""

import logging
from typing import Any
from typing import Dict
from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.db import IntegrityError
from django.db.models import Q

from apps.events.exceptions import DuplicateParticipantError
from apps.events.exceptions import ParticipantNotFoundError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.exceptions import ServiceUnavailableError
from apps.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class EventParticipantDAL:
    """Data Access Layer for EventParticipant model operations only"""

    def create_participant(self, participation_data: dict[str, Any]) -> EventParticipant:
        """Create new participant with exception translation"""
        try:
            return EventParticipant.objects.create(**participation_data)
        except IntegrityError as e:
            # Check if it's a unique constraint violation (duplicate participant)
            if 'unique_together' in str(e).lower() or 'duplicate' in str(e).lower():
                user = participation_data.get('user')
                user_id = user.id if user else 'unknown'
                logger.warning(f'Duplicate participant creation attempt for user {user_id}')
                raise DuplicateParticipantError(user_identifier=str(user_id))
            logger.exception(f'Participant creation failed - integrity error: {e}')
            msg = f'Participant creation validation failed: {e!s}'
            raise ValidationError(msg)
        except DjangoValidationError as e:
            logger.exception(f'Participant creation failed - validation error: {e}')
            msg = f'Participant data validation failed: {e!s}'
            raise ValidationError(msg)
        except DatabaseError as e:
            logger.exception(f'Participant creation failed - database error: {e}')
            msg = f'Database service unavailable: {e!s}'
            raise ServiceUnavailableError(msg)
        except Exception as e:
            logger.exception(f'Participant creation failed - unexpected error: {e}')
            msg = f'Unexpected error during participant creation: {e!s}'
            raise ServiceUnavailableError(msg)

    def get_user_participation(self, event: Event, user) -> EventParticipant:
        """Get user's participation in event with exception translation"""
        try:
            return EventParticipant.objects.get(event=event, user=user)
        except EventParticipant.DoesNotExist:
            logger.debug(f'Participant not found for user {user.id} in event {event.event_uuid}')
            raise ParticipantNotFoundError(participant_identifier=f'user_{user.id}')
        except DatabaseError as e:
            logger.exception(f'Database error while fetching participant: {e}')
            msg = f'Database service unavailable: {e!s}'
            raise ServiceUnavailableError(msg)
        except Exception as e:
            logger.exception(f'Unexpected error while fetching participant: {e}')
            msg = f'Unexpected database error: {e!s}'
            raise ServiceUnavailableError(msg)

    def get_user_participation_by_id(self, event: Event, user_id: int) -> EventParticipant | None:
        """Get user's participation by user ID - returns None if not found (no exception)"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None
        except DatabaseError as e:
            logger.exception(f'Database error while fetching participant by ID: {e}')
            msg = f'Database service unavailable: {e!s}'
            raise ServiceUnavailableError(msg)
        except Exception as e:
            logger.exception(f'Unexpected error while fetching participant by ID: {e}')
            msg = f'Unexpected database error: {e!s}'
            raise ServiceUnavailableError(msg)

    def get_user_participation_by_id_strict(self, event: Event, user_id: int) -> EventParticipant:
        """Get user's participation by user ID - raises exception if not found"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            logger.debug(f'Participant not found for user {user_id} in event {event.event_uuid}')
            raise ParticipantNotFoundError(participant_identifier=f'user_{user_id}')
        except DatabaseError as e:
            logger.exception(f'Database error while fetching participant by ID: {e}')
            msg = f'Database service unavailable: {e!s}'
            raise ServiceUnavailableError(msg)
        except Exception as e:
            logger.exception(f'Unexpected error while fetching participant by ID: {e}')
            msg = f'Unexpected database error: {e!s}'
            raise ServiceUnavailableError(msg)

    def is_user_participant(self, event: Event, user) -> bool:
        """Check if user is participant in event"""
        return EventParticipant.objects.filter(event=event, user=user).exists()

    def is_user_participant_by_id(self, event: Event, user_id: int) -> bool:
        """Check if user is participant by user ID"""
        return EventParticipant.objects.filter(event=event, user_id=user_id).exists()

    def get_event_participants(
        self,
        event: Event,
        role_filter: str | None = None,
        rsvp_filter: str | None = None,
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

    # Cache removed  # 5 minutes cache for participant count
    def get_participants_count(self, event: Event) -> int:
        """Get total participants count for event"""
        return EventParticipant.objects.filter(event=event).count()

    def get_participants_by_role(self, event: Event, role: str) -> list[EventParticipant]:
        """Get participants by role"""
        return list(
            EventParticipant.objects.filter(event=event, role=role).select_related('user').order_by('created_at')
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
            Event.objects.filter(participants_through__user_id=user_id)
            .distinct()
            .select_related('user')
            .order_by('-created_at')
        )
