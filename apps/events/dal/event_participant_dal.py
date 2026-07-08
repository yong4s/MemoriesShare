"""
Event Participant Data Access Layer - Focused on EventParticipant Model Only

Handles database operations only for the EventParticipant model.
Follows single responsibility principle for loose coupling.
"""

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.db import IntegrityError
from django.utils import timezone

from apps.events.exceptions import DuplicateParticipantError
from apps.events.exceptions import ParticipantNotFoundError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.exceptions import ServiceUnavailableError
from apps.shared.exceptions import ValidationError
from apps.shared.utils.redact import redact_secrets

logger = logging.getLogger(__name__)


class EventParticipantDAL:
    """Data Access Layer for EventParticipant model operations only"""

    def create_participant(self, participation_data: dict[str, Any]) -> EventParticipant:
        """Create new participant with exception translation.

        Programmer errors (TypeError, AttributeError, etc.) propagate by design —
        they are bugs to be fixed, not 503s to be hidden behind ServiceUnavailable.
        """
        try:
            return EventParticipant.objects.create(**participation_data)
        except IntegrityError as e:
            redacted = redact_secrets(str(e))
            # Check if it's a unique constraint violation (duplicate participant)
            if 'unique_together' in redacted.lower() or 'duplicate' in redacted.lower():
                user = participation_data.get('user')
                user_id = user.id if user else 'unknown'
                logger.warning('Duplicate participant creation attempt for user %s', user_id)
                raise DuplicateParticipantError(user_identifier=str(user_id)) from e
            logger.exception('Participant creation failed - integrity error: %s', redacted)
            raise ValidationError('Participant creation validation failed') from e
        except DjangoValidationError as e:
            logger.exception('Participant creation failed - validation error: %s', redact_secrets(str(e)))
            raise ValidationError('Participant data validation failed') from e
        except DatabaseError as e:
            logger.exception('Participant creation failed - database error: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable') from e

    def get_user_participation(self, event: Event, user) -> EventParticipant:
        """Raises ParticipantNotFoundError if the user has no participation."""
        try:
            return EventParticipant.objects.get(event=event, user=user)
        except EventParticipant.DoesNotExist as e:
            logger.debug('Participant not found for user %s in event %s', user.id, event.event_uuid)
            raise ParticipantNotFoundError(participant_identifier=f'user_{user.id}') from e
        except DatabaseError as e:
            logger.exception('Database error while fetching participant: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable') from e

    def get_user_participation_by_id(self, event: Event, user_id: int) -> EventParticipant | None:
        """Returns None if not found (no exception)."""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None
        except DatabaseError as e:
            logger.exception('Database error while fetching participant by ID: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable') from e

    def get_participant_by_pk(self, event: Event, participant_pk: int) -> EventParticipant:
        """Raises ParticipantNotFoundError if not found in this event."""
        try:
            return EventParticipant.objects.select_related('user').get(event=event, pk=participant_pk)
        except EventParticipant.DoesNotExist as e:
            raise ParticipantNotFoundError(participant_identifier=str(participant_pk)) from e
        except DatabaseError as e:
            logger.exception('Database error while fetching participant by PK: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable') from e

    def get_participant_for_invitation(self, participant_pk: int) -> EventParticipant | None:
        """Participant with event/user/participants prefetched for the invite email; None if gone."""
        try:
            return (
                EventParticipant.objects.select_related('event', 'user')
                .prefetch_related('event__participants_through__user')
                .get(pk=participant_pk)
            )
        except EventParticipant.DoesNotExist:
            return None
        except DatabaseError as e:
            logger.exception('Database error while fetching participant for invitation: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable') from e

    def mark_invitation_sent(self, participant_pk: int) -> int:
        return EventParticipant.objects.filter(pk=participant_pk).update(invitation_sent_at=timezone.now())

    def is_user_participant(self, event: Event, user) -> bool:
        """Check if user is participant in event"""
        return EventParticipant.objects.filter(event=event, user=user).exists()

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
        """Update RSVP status and stamp responded_at."""
        participation.rsvp_status = rsvp_status
        participation.responded_at = timezone.now()
        participation.save(update_fields=['rsvp_status', 'responded_at', 'updated_at'])
        return participation

    def remove_participant(self, participation: EventParticipant) -> bool:
        """Remove participant from event"""
        participation.delete()
        return True
