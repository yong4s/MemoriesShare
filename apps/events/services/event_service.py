

from typing import Any, Dict, List, Optional

from django.db import transaction

from apps.accounts.services.user_service import UserService
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.exceptions import EventCreationError, EventNotFoundError, EventPermissionError, ParticipantError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.events.services.permission_service import EventPermissionService
from apps.shared.utils.uuid_generator import generate_event_uuid
from apps.shared.storage.optimized_s3_service import OptimizedS3Service
from apps.shared.cache.cache_manager import CacheManager
import logging

logger = logging.getLogger(__name__)


class EventService:
    """Service for event business logic operations"""

    def __init__(self, dal=None, participant_dal=None, analytics_dal=None, user_service=None, s3_service=None, cache_manager=None, permission_service=None):
        # DI параметри з fallback до default імплементацій - для Container + простота
        self.dal = dal or EventDAL()
        self.participant_dal = participant_dal or EventParticipantDAL()
        self.analytics_dal = analytics_dal or EventAnalyticsDAL()
        self.user_service = user_service or UserService()
        self.s3_service = s3_service or OptimizedS3Service()
        self.cache_manager = cache_manager or CacheManager()
        self.permission_service = permission_service or EventPermissionService()

    def create_event(self, validated_data: dict[str, Any], user) -> Event:
        """
        Create event using saga pattern for proper transaction handling.
        This approach ensures data consistency across multiple services.
        """
        # Generate UUID and prepare event data
        event_data = validated_data.copy()
        event_uuid = generate_event_uuid()
        event_data['event_uuid'] = event_uuid

        s3_prefix = self._generate_s3_event_prefix(user.user_uuid, event_uuid)
        event_data['s3_prefix'] = s3_prefix

        # Step 1: Create event and participation in single transaction
        try:
            with transaction.atomic():
                event = self.dal.create_event(event_data)
                # Add creator as owner participant
                self._add_owner_participation(event, user)
                
                # Store transaction point for potential rollback
                event_created = True
        except Exception as db_error:
            logger.error(f'Failed to create event in database: {db_error}')
            raise EventCreationError(f'Failed to create event in database: {db_error!s}')

        # Step 2: Create S3 folder (outside transaction)
        try:
            self.s3_service.create_folder(s3_prefix)
            logger.info(f'Successfully created event {event_uuid} with S3 folder')
            return event
            
        except Exception as s3_error:
            logger.error(f'S3 folder creation failed for event {event_uuid}: {s3_error}')
            
            # Compensation: Clean up database changes
            try:
                with transaction.atomic():
                    # Remove participation and event in reverse order
                    participation = self.participant_dal.get_user_participation(event, user)
                    if participation:
                        participation.delete()
                    event.delete()
                    logger.info(f'Successfully rolled back event {event_uuid} after S3 failure')
                    
            except Exception as rollback_error:
                logger.critical(
                    f'CRITICAL: Failed to rollback event {event_uuid} after S3 failure. '
                    f'Manual cleanup required. S3 error: {s3_error}, Rollback error: {rollback_error}'
                )
                raise EventCreationError(
                    f'Failed to create S3 folder and rollback failed. '
                    f'Event {event_uuid} requires manual cleanup. '
                    f'S3 error: {s3_error!s}, Rollback error: {rollback_error!s}'
                )
                
            raise EventCreationError(f'Failed to create S3 folder, event creation rolled back: {s3_error!s}')

    def get_event_detail(self, event_uuid: str, user_id: int) -> Event:

        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid_optimized(event_uuid)

        if not self.can_user_access_event(event, user_id):
            raise EventPermissionError(action="access", event_id=event_uuid)

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

        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.can_user_modify_event(event, user_id):
            raise EventPermissionError(action="modify", event_id=event_uuid)

        updated_event = self.dal.update_event(event, validated_data)
        
        # Schedule cache invalidation after transaction commit
        def invalidate_caches():
            try:
                self._invalidate_event_caches(event_uuid, ['detail', 'statistics'])
                self._invalidate_user_caches(user_id, ['events'])
            except Exception as e:
                logger.error(f'Failed to invalidate caches after event update {event_uuid}: {e}')
                # In production, consider sending to dead letter queue for retry
        
        transaction.on_commit(invalidate_caches)
        
        return updated_event

    @transaction.atomic
    def delete_event(self, event_uuid: str, user_id: int) -> bool:

        # DAL now raises EventNotFoundError if event doesn't exist  
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.is_event_owner(event, user_id):
            raise EventPermissionError(action="delete", event_id=event_uuid)

        result = self.dal.delete_event(event)
        
        # Delete S3 folder after database deletion
        try:
            self.s3_service.delete_folder(event.s3_prefix)
        except Exception as s3_error:
            logger.warning(f'Failed to delete S3 folder for event {event_uuid}: {s3_error}')
            # Continue - event is deleted from DB, S3 cleanup can be done later

        # Schedule cache invalidation after transaction commit
        def invalidate_caches():
            try:
                self._invalidate_event_caches(event_uuid, ['detail', 'statistics', 'participants'])
                self._invalidate_user_caches(user_id, ['events', 'analytics'])
            except Exception as e:
                logger.error(f'Failed to invalidate caches after event deletion {event_uuid}: {e}')
                # In production, consider sending to dead letter queue for retry
        
        transaction.on_commit(invalidate_caches)
        
        return result

    # PARTICIPANT MANAGEMENT

    def get_event_participants(
        self, event_uuid: str, requesting_user_id: int, role_filter: str | None = None, rsvp_filter: str | None = None
    ) -> list[EventParticipant]:

        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.can_user_access_event(event, requesting_user_id):
            raise EventPermissionError(action="access", event_id=event_uuid)

        return self.participant_dal.get_event_participants(event, role_filter, rsvp_filter)

    @transaction.atomic
    def add_participant_to_event(
        self,
        event_uuid: str,
        user,
        role: str = EventParticipant.Role.GUEST,
        guest_name: str = '',
        guest_email: str = '',
        requesting_user_id: int = None,
        invite_token: str = None,
    ) -> EventParticipant:

        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        # Permission check (skip for invite tokens)
        if requesting_user_id and not invite_token:
            if not self.can_user_modify_event(event, requesting_user_id):
                raise EventPermissionError('You cannot add participants to this event')

        # Check if user is already a participant
        if self.participant_dal.is_user_participant(event, user):
            raise ParticipantError('User is already a participant in this event')

        # Create participation record
        participation_data = {
            'event': event,
            'user': user,
            'role': role,
            'guest_name': guest_name or user.display_name,
            'guest_email': guest_email or getattr(user, 'email', ''),
            'invite_token_used': invite_token,
            'rsvp_status': EventParticipant.RsvpStatus.PENDING,
        }

        return self.participant_dal.create_participant(participation_data)

    @transaction.atomic
    def remove_participant_from_event(self, event_uuid: str, user, requesting_user_id: int) -> bool:

        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        # Permission check
        if not self.can_user_modify_event(event, requesting_user_id):
            raise EventPermissionError('You cannot remove participants from this event')

        # Cannot remove event owner
        if self.is_event_owner(event, user.id):
            raise ParticipantError('Cannot remove event owner from event')

        participation = self.participant_dal.get_user_participation(event, user)
        if not participation:
            raise ParticipantError('User is not a participant in this event')

        return self.participant_dal.remove_participant(participation)

    @transaction.atomic
    def update_participant_rsvp(
        self, event_uuid: str, user, rsvp_status: str, requesting_user_id: int
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

        participation = self.participant_dal.get_user_participation(event, user)
        if not participation:
            raise ParticipantError('User is not a participant in this event')

        # Users can update their own RSVP, or event owner can update any RSVP
        if requesting_user_id != user.id and not self.is_event_owner(event, requesting_user_id):
            raise EventPermissionError('You can only update your own RSVP status')

        return self.participant_dal.update_participant_rsvp(participation, rsvp_status)

    @transaction.atomic
    def invite_guest_to_event(
        self, event_uuid: str, guest_name: str, guest_email: str, requesting_user_id: int, user_service: UserService
    ) -> tuple[EventParticipant]:
        """
        Invite guest user to event with comprehensive validation

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
            EventValidationError: If guest data is invalid
        """
        # Validate guest data at service layer
        self._validate_guest_invitation_data(guest_name, guest_email)
        
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            raise EventNotFoundError(f'Event {event_uuid} not found')

        if not self.can_user_modify_event(event, requesting_user_id):
            raise EventPermissionError('You cannot invite guests to this event')
        
        # Validate event status
        self._validate_event_status(event)

        # Create guest user
        guest_user = user_service.create_guest_user(guest_name=guest_name, guest_email=guest_email)

        # Add as participant
        participation = self.add_participant_to_event(
            event_uuid=event_uuid,
            user=guest_user,
            role=EventParticipant.Role.GUEST,
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
        return self.is_event_owner(event, user_id) or self.participant_dal.is_user_participant_by_id(event, user_id)

    def can_user_modify_event(self, event: Event, user_id: int) -> bool:
        """Check if user can modify event"""
        if self.is_event_owner(event, user_id):
            return True

        # Check if user is moderator
        participation = self.participant_dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == 'MODERATOR'

    def is_event_owner(self, event: Event, user_id: int) -> bool:
        """Check if user is event owner via EventParticipant"""
        participation = self.participant_dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == 'OWNER'

    def get_user_participation_in_event(self, event: Event, user) -> EventParticipant | None:
        """Get user's participation in event"""
        return self.participant_dal.get_user_participation(event, user)

    # =============================================================================
    # VALIDATION HELPERS
    # =============================================================================
    
    def _validate_guest_invitation_data(self, guest_name: str, guest_email: str) -> None:
        """
        Validate guest invitation data at service layer
        
        Args:
            guest_name: Guest name to validate
            guest_email: Guest email to validate
            
        Raises:
            EventValidationError: If validation fails
        """
        from apps.events.exceptions import EventValidationError
        import re
        
        errors = []
        
        # Validate guest name
        if not guest_name or not guest_name.strip():
            errors.append('Guest name is required')
        elif len(guest_name.strip()) < 2:
            errors.append('Guest name must be at least 2 characters long')
        elif len(guest_name.strip()) > 255:
            errors.append('Guest name cannot exceed 255 characters')
        elif not re.match(r'^[a-zA-Z\s\u0100-\u017F\u0400-\u04FF\'.-]+$', guest_name.strip()):
            errors.append('Guest name contains invalid characters')
            
        # Validate guest email (if provided)
        if guest_email and guest_email.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, guest_email.strip()):
                errors.append('Guest email format is invalid')
            elif len(guest_email.strip()) > 254:
                errors.append('Guest email cannot exceed 254 characters')
        
        if errors:
            raise EventValidationError(f'Guest invitation validation failed: {", ".join(errors)}')
    
    def _validate_event_capacity(self, event: Event) -> None:
        """
        Validate event capacity constraints (if implemented)
        
        Args:
            event: Event to check capacity for
            
        Raises:
            EventValidationError: If capacity exceeded
        """
        # Placeholder for future capacity validation
        # Can be extended to check max_participants if field is added to Event model
        pass
    
    def _validate_event_status(self, event: Event) -> None:
        """
        Validate event status for modifications
        
        Args:
            event: Event to validate
            
        Raises:
            EventValidationError: If event cannot be modified
        """
        from django.utils import timezone
        from apps.events.exceptions import EventValidationError
        
        # Check if event is in the past
        if event.date < timezone.now().date():
            raise EventValidationError('Cannot invite guests to past events')

    # =============================================================================
    # PRIVATE HELPERS
    # =============================================================================

    def _add_owner_participation(self, event: Event, user) -> EventParticipant:
        """Add event creator as owner participant"""
        participation_data = {
            'event': event,
            'user': user,
            'role': EventParticipant.Role.OWNER,
            'guest_name': user.display_name,
            'guest_email': getattr(user, 'email', ''),
            'rsvp_status': EventParticipant.RsvpStatus.ACCEPTED,
        }
        return self.participant_dal.create_participant(participation_data)

    def _generate_s3_event_prefix(self, user_uuid, event_uuid):
        """Generate event prefix"""
        return f'users/{user_uuid}/events/{event_uuid}'

    def _invalidate_event_caches(self, event_uuid: str, cache_types: list[str]) -> None:
        """Safely invalidate event-related caches with retry mechanism"""
        for cache_type in cache_types:
            try:
                self.cache_manager.invalidate_event_cache(event_uuid, cache_type)
                logger.debug(f"Successfully invalidated event cache {cache_type} for {event_uuid}")
            except Exception as e:
                # Log cache errors but don't fail the operation
                logger.warning(f"Failed to invalidate event cache {cache_type} for {event_uuid}: {e}")
                # In production, could implement retry logic or send to message queue
    
    def _invalidate_user_caches(self, user_id: int, cache_types: list[str]) -> None:
        """Safely invalidate user-related caches with retry mechanism"""
        for cache_type in cache_types:
            try:
                self.cache_manager.invalidate_user_cache(user_id, cache_type)
                logger.debug(f"Successfully invalidated user cache {cache_type} for user {user_id}")
            except Exception as e:
                # Log cache errors but don't fail the operation
                logger.warning(f"Failed to invalidate user cache {cache_type} for user {user_id}: {e}")
                # In production, could implement retry logic or send to message queue
