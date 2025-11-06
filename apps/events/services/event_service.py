"""
Clean EventService for Business Logic

Handles all event-related business operations while working with the
"dumb" Event model. Follows SOLID principles and 3-layer architecture.
"""

import uuid
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.accounts.models.custom_user import CustomUser
from apps.accounts.services.user_service import UserService
from apps.events.dal.event_dal import EventDAL
from apps.events.exceptions import EventCreationError
from apps.events.exceptions import EventNotFoundError
from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import ParticipantError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.storage.optimized_s3_service import OptimizedS3Service


class EventService:
    """Service for event business logic operations"""

    def __init__(self):
        self.dal = EventDAL()
        self.user_service = UserService()
        self.s3_service = OptimizedS3Service()

    @transaction.atomic
    def create_event(self, validated_data: dict[str, Any], user: CustomUser) -> Event:
        """
        Create new event with automatic owner participation

        Args:
            validated_data: Event creation data
            user: Event creator (owner)

        Returns:
            Event: Created event instance

        Raises:
            EventCreationError: If event creation fails
        """
        try:
            # Generate UUID and prepare event data
            event_data = validated_data.copy()
            event_uuid = uuid.uuid4()
            event_data['event_uuid'] = event_uuid
            event_data['user'] = user

            # Create S3 folder structure: users/{user_uuid}/events/{event_uuid}
            s3_prefix = f'users/{user.user_uuid}/events/{event_uuid}'
            event_data['s3_prefix'] = s3_prefix

            # Create S3 folder
            try:
                self.s3_service.create_folder(s3_prefix)
            except Exception as s3_error:
                raise EventCreationError(f'Failed to create S3 folder: {s3_error!s}')

            # Create event through DAL
            event = self.dal.create_event(event_data)

            # Add creator as owner participant
            self._add_owner_participation(event, user)

            return event

        except Exception as e:
            raise EventCreationError(f'Failed to create event: {e!s}')

    def get_event_detail(self, event_uuid: str, user_id: int) -> Event:
        """
        Get event details with permission check

        Args:
            event_uuid: Event UUID
            user_id: Requesting user ID

        Returns:
            Event: Event instance with optimized data

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user lacks access
        """
        event = self.dal.get_event_by_uuid_optimized(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.can_user_access_event(event, user_id):
            raise EventPermissionError("You don't have access to this event")

        return event

    def get_events_list(self, filters: dict[str, Any], user_id: int) -> dict[str, Any]:
        """
        Get paginated list of user's events

        Args:
            filters: Query filters and pagination params
            user_id: User ID

        Returns:
            Dict containing events and pagination info
        """
        return self.dal.get_user_events_paginated(user_id, filters)

    @transaction.atomic
    def update_event(self, event_uuid: str, validated_data: dict[str, Any], user_id: int) -> Event:
        """
        Update existing event

        Args:
            event_uuid: Event UUID
            validated_data: Update data
            user_id: Requesting user ID

        Returns:
            Event: Updated event instance

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user cannot modify
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.can_user_modify_event(event, user_id):
            raise EventPermissionError('You cannot modify this event')

        return self.dal.update_event(event, validated_data)

    @transaction.atomic
    def delete_event(self, event_uuid: str, user_id: int) -> bool:
        """
        Delete event (only by owner)

        Args:
            event_uuid: Event UUID
            user_id: Requesting user ID

        Returns:
            bool: True if deleted successfully

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user is not owner
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.is_event_owner(event, user_id):
            raise EventPermissionError('Only event owner can delete the event')

        return self.dal.delete_event(event)

    # =============================================================================
    # PARTICIPANT MANAGEMENT
    # =============================================================================

    def get_event_participants(
        self, event_uuid: str, requesting_user_id: int, role_filter: str | None = None, rsvp_filter: str | None = None
    ) -> list[EventParticipant]:
        """
        Get event participants with permission check

        Args:
            event_uuid: Event UUID
            requesting_user_id: User requesting the list
            role_filter: Optional role filter
            rsvp_filter: Optional RSVP status filter

        Returns:
            List of EventParticipant instances

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user lacks access
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.can_user_access_event(event, requesting_user_id):
            raise EventPermissionError("You don't have access to this event")

        return self.dal.get_event_participants(event, role_filter, rsvp_filter)

    @transaction.atomic
    def add_participant_to_event(
        self,
        event_uuid: str,
        user: CustomUser,
        role: str = 'GUEST',
        guest_name: str = '',
        guest_email: str = '',
        requesting_user_id: int = None,
        invite_token: str = None,
    ) -> EventParticipant:
        """
        Add participant to event

        Args:
            event_uuid: Event UUID
            user: User to add as participant
            role: Participant role
            guest_name: Guest name (for guest users)
            guest_email: Guest email (for guest users)
            requesting_user_id: User making the request
            invite_token: Optional invitation token

        Returns:
            EventParticipant: Created participation record

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user cannot add participants
            ParticipantError: If participant already exists or validation fails
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        # Permission check (skip for invite tokens)
        if requesting_user_id and not invite_token:
            if not self.can_user_modify_event(event, requesting_user_id):
                raise EventPermissionError('You cannot add participants to this event')

        # Check if user is already a participant
        if self.dal.is_user_participant(event, user):
            raise ParticipantError('User is already a participant in this event')

        # Create participation record
        participation_data = {
            'event': event,
            'user': user,
            'role': role,
            'guest_name': guest_name or user.display_name,
            'guest_email': guest_email or getattr(user, 'email', ''),
            'invite_token_used': invite_token,
            'rsvp_status': 'PENDING',
        }

        return self.dal.create_participant(participation_data)

    @transaction.atomic
    def remove_participant_from_event(self, event_uuid: str, user: CustomUser, requesting_user_id: int) -> bool:
        """
        Remove participant from event

        Args:
            event_uuid: Event UUID
            user: User to remove
            requesting_user_id: User making the request

        Returns:
            bool: True if removed successfully

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user cannot remove participants
            ParticipantError: If participant not found
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        # Permission check
        if not self.can_user_modify_event(event, requesting_user_id):
            raise EventPermissionError('You cannot remove participants from this event')

        # Cannot remove event owner
        if self.is_event_owner(event, user.id):
            raise ParticipantError('Cannot remove event owner from event')

        participation = self.dal.get_user_participation(event, user)
        if not participation:
            raise ParticipantError('User is not a participant in this event')

        return self.dal.remove_participant(participation)

    @transaction.atomic
    def update_participant_rsvp(
        self, event_uuid: str, user: CustomUser, rsvp_status: str, requesting_user_id: int
    ) -> EventParticipant:
        """
        Update participant RSVP status

        Args:
            event_uuid: Event UUID
            user: User whose RSVP to update
            rsvp_status: New RSVP status
            requesting_user_id: User making the request

        Returns:
            EventParticipant: Updated participation record

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user cannot update RSVP
            ParticipantError: If participant not found
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        participation = self.dal.get_user_participation(event, user)
        if not participation:
            raise ParticipantError('User is not a participant in this event')

        # Users can update their own RSVP, or event owner can update any RSVP
        if requesting_user_id != user.id and not self.is_event_owner(event, requesting_user_id):
            raise EventPermissionError('You can only update your own RSVP status')

        return self.dal.update_participant_rsvp(participation, rsvp_status)

    @transaction.atomic
    def invite_guest_to_event(
        self, event_uuid: str, guest_name: str, guest_email: str, requesting_user_id: int, user_service: UserService
    ) -> tuple[CustomUser, EventParticipant]:
        """
        Invite guest user to event

        Args:
            event_uuid: Event UUID
            guest_name: Guest's name
            guest_email: Guest's email
            requesting_user_id: User sending invitation
            user_service: UserService instance

        Returns:
            Tuple of (guest_user, participation)

        Raises:
            EventNotFoundError: If event not found
            EventPermissionError: If user cannot invite guests
        """
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.can_user_modify_event(event, requesting_user_id):
            raise EventPermissionError('You cannot invite guests to this event')

        # Create guest user
        guest_user = user_service.create_guest_user(guest_name=guest_name, guest_email=guest_email)

        # Add as participant
        participation = self.add_participant_to_event(
            event_uuid=event_uuid,
            user=guest_user,
            role='GUEST',
            guest_name=guest_name,
            guest_email=guest_email,
            requesting_user_id=requesting_user_id,
        )

        return guest_user, participation

    # =============================================================================
    # PERMISSION HELPERS
    # =============================================================================

    def can_user_access_event(self, event: Event, user_id: int) -> bool:
        """Check if user can access event"""
        return self.is_event_owner(event, user_id) or self.dal.is_user_participant_by_id(event, user_id)

    def can_user_modify_event(self, event: Event, user_id: int) -> bool:
        """Check if user can modify event"""
        if self.is_event_owner(event, user_id):
            return True

        # Check if user is moderator
        participation = self.dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == 'MODERATOR'

    def is_event_owner(self, event: Event, user_id: int) -> bool:
        """Check if user is event owner"""
        return event.user_id == user_id

    def get_user_participation_in_event(self, event: Event, user: CustomUser) -> EventParticipant | None:
        """Get user's participation in event"""
        return self.dal.get_user_participation(event, user)

    # =============================================================================
    # PRIVATE HELPERS
    # =============================================================================

    def _add_owner_participation(self, event: Event, user: CustomUser) -> EventParticipant:
        """Add event creator as owner participant"""
        participation_data = {
            'event': event,
            'user': user,
            'role': 'OWNER',
            'guest_name': user.display_name,
            'guest_email': getattr(user, 'email', ''),
            'rsvp_status': 'ACCEPTED',
        }
        return self.dal.create_participant(participation_data)
