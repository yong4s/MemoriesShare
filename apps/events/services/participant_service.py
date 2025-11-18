"""EventParticipant service for business logic operations."""

import logging
from typing import Any
from typing import Dict
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models.custom_user import CustomUser
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
# Removed cache decorators - using simple direct caching in services

logger = logging.getLogger(__name__)


class EventParticipantService:
    """Service for event participant business logic operations"""

    def __init__(self, validator=None, dal=None):
        self.validator = validator
        self.dal = dal or EventParticipant.objects

    @transaction.atomic
    def add_participant(self, event: Event, user: CustomUser, role: str, **kwargs) -> EventParticipant:
        """Add participant to event with validation."""
        if self.validator:
            self.validator.validate_add_participant(event, user, role)
        participant_data = {
            'event': event,
            'user': user,
            'role': role,
            'rsvp_status': kwargs.get('rsvp_status', EventParticipant.RsvpStatus.PENDING),
        }

        # Handle guest-specific data
        if user.is_guest:
            participant_data.update(
                {
                    'guest_name': kwargs.get('guest_name', user.display_name),
                    'guest_email': kwargs.get('guest_email', ''),
                    'guest_phone': kwargs.get('guest_phone', ''),
                    'dietary_preferences': kwargs.get('dietary_preferences', ''),
                }
            )

        # Handle invitation metadata
        if kwargs.get('invite_token_used'):
            participant_data['invite_token_used'] = kwargs['invite_token_used']
        if kwargs.get('join_method'):
            participant_data['join_method'] = kwargs['join_method']
        if kwargs.get('invitation_sent_at'):
            participant_data['invitation_sent_at'] = kwargs['invitation_sent_at']

        try:
            # 3. Create participant (DAL)
            participant = self.dal.create(**participant_data)
            logger.info(f'Participant {user.id} added to event {event.id} with role {role}')
            return participant
        except IntegrityError:
            # Handle unique_together constraint violation
            raise ValidationError('User is already a participant in this event')

    def accept_invitation(self, participant: EventParticipant) -> EventParticipant:
        """
        Handle business logic for accepting an invitation.

        Args:
            participant: EventParticipant instance

        Returns:
            EventParticipant: Updated participant
        """
        if participant.rsvp_status == EventParticipant.RsvpStatus.ACCEPTED:
            # Already accepted, nothing to do
            return participant

        # Update RSVP status and response time
        participant.rsvp_status = EventParticipant.RsvpStatus.ACCEPTED
        participant.responded_at = timezone.now()
        participant.save(update_fields=['rsvp_status', 'responded_at'])

        logger.info(f'Participant {participant.id} accepted invitation to event {participant.event.id}')
        return participant

    def decline_invitation(self, participant: EventParticipant) -> EventParticipant:
        """
        Handle business logic for declining an invitation.

        Args:
            participant: EventParticipant instance

        Returns:
            EventParticipant: Updated participant
        """
        if participant.rsvp_status == EventParticipant.RsvpStatus.DECLINED:
            # Already declined, nothing to do
            return participant

        # Update RSVP status and response time
        participant.rsvp_status = EventParticipant.RsvpStatus.DECLINED
        participant.responded_at = timezone.now()
        participant.save(update_fields=['rsvp_status', 'responded_at'])

        logger.info(f'Participant {participant.id} declined invitation to event {participant.event.id}')
        return participant

    # Cache removed
    # Cache removed
    def update_rsvp_status(self, participant: EventParticipant, new_status: str) -> EventParticipant:
        """
        Update participant RSVP status with business logic.

        Args:
            participant: EventParticipant instance
            new_status: New RSVP status

        Returns:
            EventParticipant: Updated participant
        """
        if participant.rsvp_status == new_status:
            # No change needed
            return participant

        old_status = participant.rsvp_status
        participant.rsvp_status = new_status

        # Set response timestamp for status changes from PENDING
        if old_status == EventParticipant.RsvpStatus.PENDING:
            participant.responded_at = timezone.now()
            participant.save(update_fields=['rsvp_status', 'responded_at'])
        else:
            participant.save(update_fields=['rsvp_status'])

        logger.info(f'Participant {participant.id} RSVP status changed from {old_status} to {new_status}')
        return participant

    def send_invitation(self, participant: EventParticipant) -> EventParticipant:
        """
        Mark invitation as sent with timestamp.

        Args:
            participant: EventParticipant instance

        Returns:
            EventParticipant: Updated participant
        """
        if participant.invitation_sent_at:
            # Already sent, update timestamp
            logger.warning(f'Invitation already sent for participant {participant.id}, updating timestamp')

        participant.invitation_sent_at = timezone.now()
        participant.save(update_fields=['invitation_sent_at'])

        logger.info(f'Invitation sent to participant {participant.id} for event {participant.event.id}')
        return participant

    @transaction.atomic
    def remove_participant(self, participant: EventParticipant) -> bool:
        """
        Remove participant from event with business logic checks.

        Args:
            participant: EventParticipant instance to remove

        Returns:
            bool: True if removed successfully

        Raises:
            ValidationError: If participant cannot be removed
        """
        # Business rule: Cannot remove event owner
        if participant.role == EventParticipant.Role.OWNER:
            raise ValidationError('Cannot remove event owner from event')

        event_id = participant.event.id
        participant_id = participant.id

        # Delete the participant
        participant.delete()

        logger.info(f'Participant {participant_id} removed from event {event_id}')
        return True

    def update_guest_info(self, participant: EventParticipant, guest_data: dict[str, Any]) -> EventParticipant:
        """
        Update guest-specific information.

        Args:
            participant: EventParticipant instance
            guest_data: Dictionary with guest information

        Returns:
            EventParticipant: Updated participant
        """
        if not participant.user.is_guest:
            raise ValidationError('Cannot update guest info for registered users')

        update_fields = []

        # Update guest-specific fields
        if 'guest_name' in guest_data:
            participant.guest_name = guest_data['guest_name'].strip()
            update_fields.append('guest_name')

        if 'guest_email' in guest_data:
            participant.guest_email = guest_data['guest_email'].lower().strip()
            update_fields.append('guest_email')

        if 'guest_phone' in guest_data:
            participant.guest_phone = guest_data['guest_phone'].strip()
            update_fields.append('guest_phone')

        if 'dietary_preferences' in guest_data:
            participant.dietary_preferences = guest_data['dietary_preferences'].strip()
            update_fields.append('dietary_preferences')

        if update_fields:
            participant.save(update_fields=update_fields)
            logger.info(f'Updated guest info for participant {participant.id}: {update_fields}')

        return participant

    def get_participation_stats(self, event: Event) -> dict[str, int]:
        """Get participation statistics for an event."""
        from django.db.models import Count
        from django.db.models import Q

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

    def bulk_update_rsvp(self, participants: list, new_status: str) -> int:
        """
        Bulk update RSVP status for multiple participants.

        Args:
            participants: List of EventParticipant instances
            new_status: New RSVP status

        Returns:
            int: Number of participants updated
        """
        participant_ids = [p.id for p in participants]

        # Use bulk_update for performance
        updated_count = (
            EventParticipant.objects.filter(id__in=participant_ids)
            .exclude(rsvp_status=new_status)
            .update(rsvp_status=new_status, responded_at=timezone.now())
        )

        logger.info(f'Bulk updated RSVP status to {new_status} for {updated_count} participants')
        return updated_count
