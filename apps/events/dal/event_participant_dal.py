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
from django.db.models import Count
from django.db.models import Q
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
                raise DuplicateParticipantError(user_identifier=str(user_id))
            logger.exception('Participant creation failed - integrity error: %s', redacted)
            raise ValidationError('Participant creation validation failed')
        except DjangoValidationError as e:
            logger.exception('Participant creation failed - validation error: %s', redact_secrets(str(e)))
            raise ValidationError('Participant data validation failed')
        except DatabaseError as e:
            logger.exception('Participant creation failed - database error: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable')

    def get_user_participation(self, event: Event, user) -> EventParticipant:
        """Get user's participation in event with exception translation"""
        try:
            return EventParticipant.objects.get(event=event, user=user)
        except EventParticipant.DoesNotExist:
            logger.debug('Participant not found for user %s in event %s', user.id, event.event_uuid)
            raise ParticipantNotFoundError(participant_identifier=f'user_{user.id}')
        except DatabaseError as e:
            logger.exception('Database error while fetching participant: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable')

    def get_user_participation_by_id(self, event: Event, user_id: int) -> EventParticipant | None:
        """Get user's participation by user ID - returns None if not found (no exception)"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            return None
        except DatabaseError as e:
            logger.exception('Database error while fetching participant by ID: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable')

    def get_user_participation_by_id_strict(self, event: Event, user_id: int) -> EventParticipant:
        """Get user's participation by user ID - raises exception if not found"""
        try:
            return EventParticipant.objects.get(event=event, user_id=user_id)
        except EventParticipant.DoesNotExist:
            logger.debug('Participant not found for user %s in event %s', user_id, event.event_uuid)
            raise ParticipantNotFoundError(participant_identifier=f'user_{user_id}')
        except DatabaseError as e:
            logger.exception('Database error while fetching participant by ID: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable')

    def get_participant_by_pk(self, event: Event, participant_pk: int) -> EventParticipant:
        """Get a single participant by primary key within an event. Raises ParticipantNotFoundError."""
        try:
            return EventParticipant.objects.select_related('user').get(event=event, pk=participant_pk)
        except EventParticipant.DoesNotExist:
            raise ParticipantNotFoundError(participant_identifier=str(participant_pk))
        except DatabaseError as e:
            logger.exception('Database error while fetching participant by PK: %s', redact_secrets(str(e)))
            raise ServiceUnavailableError('Database service unavailable')

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

    def get_participation_stats(self, event: Event) -> dict[str, int]:
        """Aggregate participation counts for ``event`` (totals by role + RSVP).

        Single GROUP BY query — cheap on the covering ``(event, role, rsvp_status)``
        index recommended in the perf plan.
        """
        return EventParticipant.objects.filter(event=event).aggregate(
            total=Count('id'),
            owners=Count('id', filter=Q(role=EventParticipant.Role.OWNER)),
            guests=Count('id', filter=Q(role=EventParticipant.Role.GUEST)),
            moderators=Count('id', filter=Q(role=EventParticipant.Role.MODERATOR)),
            accepted=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.ACCEPTED)),
            declined=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.DECLINED)),
            pending=Count('id', filter=Q(rsvp_status=EventParticipant.RsvpStatus.PENDING)),
            attending=Count(
                'id',
                filter=Q(
                    rsvp_status__in=[
                        EventParticipant.RsvpStatus.ACCEPTED,
                        EventParticipant.RsvpStatus.CONFIRMED_PLUS_ONE,
                        EventParticipant.RsvpStatus.TENTATIVE,
                        EventParticipant.RsvpStatus.MAYBE,
                    ]
                ),
            ),
        )

    def bulk_update_rsvp_status(self, participant_ids: list[int], new_status: str) -> int:
        """Bulk-set ``new_status`` on the given participants. Returns updated row count.

        Skips rows already in ``new_status`` so ``responded_at`` is only stamped on
        actual transitions.
        """
        return (
            EventParticipant.objects.filter(id__in=participant_ids)
            .exclude(rsvp_status=new_status)
            .update(rsvp_status=new_status, responded_at=timezone.now())
        )
