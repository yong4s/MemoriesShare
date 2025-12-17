import logging
import re
import uuid
from typing import Any

from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.user_service import UserService
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.exceptions import EventCreationError
from apps.events.exceptions import EventNotFoundError
from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import EventValidationError
from apps.events.exceptions import ParticipantError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.cache.cache_manager import CacheManager
from apps.shared.storage.optimized_s3_service import OptimizedS3Service
from apps.shared.utils.paginator import ServicePaginator

logger = logging.getLogger(__name__)


class EventService:
    """Service for event business logic operations"""

    def __init__(
        self,
        dal=None,
        participant_dal=None,
        user_service=None,
        s3_service=None,
        cache_manager=None,
    ):
        self.dal = dal or EventDAL()
        self.participant_dal = participant_dal or EventParticipantDAL()
        self.user_service = user_service or UserService()
        self.s3_service = s3_service or OptimizedS3Service()
        self.cache_manager = cache_manager or CacheManager()

    def create_event(self, user, validated_data: dict[str, Any]) -> Event:
        """Create event with lazy S3 folder creation on first file upload"""
        event_uuid = uuid.uuid4()
        s3_prefix = self._generate_s3_event_prefix(str(user.user_uuid), str(event_uuid))

        event_data = validated_data.copy()
        event_data['event_uuid'] = event_uuid
        event_data['s3_prefix'] = s3_prefix
        event_data['user'] = user

        try:
            with transaction.atomic():
                event = self.dal.create_event(event_data)
                self._add_owner_participation(event, user)
                return event
        except Exception as db_error:
            logger.exception(f'Failed to create event in DB: {db_error}')
            msg = f'Database error: {db_error!s}'
            raise EventCreationError(msg)

    def get_event_detail(self, event_uuid: str, user_id: int) -> Event:
        event = self.dal.get_event_by_uuid_optimized(event_uuid)
        if not self.can_user_access_event(event, user_id):
            raise EventPermissionError(action='access', event_id=event_uuid)
        return event

    def get_events_list(self, filters: dict[str, Any], user) -> dict[str, Any]:
        page = filters.get('page', 1)
        page_size = min(filters.get('page_size', 20), 100)  # Limit max page size
        search = filters.get('search', '').strip()
        owned_only = filters.get('owned_only', False)

        if owned_only:
            queryset = self.dal.get_owned_events_queryset(user.id)
        else:
            queryset = self.dal.get_user_events_queryset(user.id)

        queryset = queryset.search(search).with_statistics_ordered()

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

    @transaction.atomic
    def update_event(self, event_uuid: str, validated_data: dict[str, Any], user) -> Event:
        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.can_user_modify_event(event, user.id):
            raise EventPermissionError(action='modify', event_id=event_uuid)

        updated_event = self.dal.update_event(event, validated_data)

        transaction.on_commit(
            lambda: self._invalidate_caches(event_uuid, user.id, ['detail', 'statistics'], ['events'])
        )

        return updated_event

    @transaction.atomic
    def delete_event(self, event_uuid: str, user_id: int) -> bool:
        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.is_event_owner(event, user_id):
            raise EventPermissionError(action='delete', event_id=event_uuid)

        result = self.dal.delete_event(event)

        try:
            self.s3_service.delete_folder(event.s3_prefix)
            logger.debug(f'Successfully cleaned up S3 folder for event {event_uuid}')
        except Exception as s3_error:
            logger.warning(f'Non-critical: Failed to delete S3 folder for event {event_uuid}: {s3_error}')

        transaction.on_commit(
            lambda: self._invalidate_caches(
                event_uuid,
                user_id,
                ['detail', 'statistics', 'participants'],
                ['events', 'analytics'],
            )
        )

        return result

    def get_event_participants(
        self,
        event_uuid: str,
        requesting_user_id: int,
        role_filter: str | None = None,
        rsvp_filter: str | None = None,
    ) -> list[EventParticipant]:
        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid(event_uuid)

        if not self.can_user_access_event(event, requesting_user_id):
            raise EventPermissionError(action='access', event_id=event_uuid)

        return self.participant_dal.get_event_participants(event, role_filter, rsvp_filter)

    @transaction.atomic
    def add_participant_to_event(
        self,
        event_uuid: str,
        user,
        role: str = EventParticipant.Role.GUEST,
        guest_name: str = '',
        guest_email: str = '',
        requesting_user_id: int | None = None,
        invite_token: str | None = None,
    ) -> EventParticipant:
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            msg = f'Event {event_uuid} not found'
            raise EventNotFoundError(msg)

        if requesting_user_id and not invite_token and not self.can_user_modify_event(event, requesting_user_id):
            msg = 'You cannot add participants to this event'
            raise EventPermissionError(msg)

        if self.participant_dal.is_user_participant(event, user):
            msg = 'User is already a participant in this event'
            raise ParticipantError(msg)

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
            msg = f'Event {event_uuid} not found'
            raise EventNotFoundError(msg)

        # Permission check
        if not self.can_user_modify_event(event, requesting_user_id):
            msg = 'You cannot remove participants from this event'
            raise EventPermissionError(msg)

        if self.is_event_owner(event, user.id):
            msg = 'Cannot remove event owner from event'
            raise ParticipantError(msg)

        participation = self.participant_dal.get_user_participation(event, user)
        if not participation:
            msg = 'User is not a participant in this event'
            raise ParticipantError(msg)

        return self.participant_dal.remove_participant(participation)

    @transaction.atomic
    def update_participant_rsvp(
        self, event_uuid: str, user, rsvp_status: str, requesting_user_id: int
    ) -> EventParticipant:
        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            msg = f'Event {event_uuid} not found'
            raise EventNotFoundError(msg)

        participation = self.participant_dal.get_user_participation(event, user)
        if not participation:
            msg = 'User is not a participant in this event'
            raise ParticipantError(msg)

        if requesting_user_id != user.id and not self.is_event_owner(event, requesting_user_id):
            msg = 'You can only update your own RSVP status'
            raise EventPermissionError(msg)

        return self.participant_dal.update_participant_rsvp(participation, rsvp_status)

    @transaction.atomic
    def invite_guest_to_event(
        self,
        event_uuid: str,
        guest_name: str,
        guest_email: str,
        requesting_user_id: int,
        user_service: UserService,
    ) -> tuple[EventParticipant]:
        self._validate_guest_invitation_data(guest_name, guest_email)

        event = self.dal.get_event_by_uuid(event_uuid)
        if not event:
            msg = f'Event {event_uuid} not found'
            raise EventNotFoundError(msg)

        if not self.can_user_modify_event(event, requesting_user_id):
            msg = 'You cannot invite guests to this event'
            raise EventPermissionError(msg)

        self._validate_event_status(event)

        guest_user = user_service.create_guest_user(guest_name=guest_name, guest_email=guest_email)

        participation = self.add_participant_to_event(
            event_uuid=event_uuid,
            user=guest_user,
            role=EventParticipant.Role.GUEST,
            guest_name=guest_name,
            guest_email=guest_email,
            requesting_user_id=requesting_user_id,
        )

        return guest_user, participation

    def can_user_access_event(self, event: Event, user_id: int) -> bool:
        """Check if user can access event"""
        return (
            event.user_id == user_id
            or event.is_public
            or self.participant_dal.is_user_participant_by_id(event, user_id)
        )

    def can_user_modify_event(self, event: Event, user_id: int) -> bool:
        """Check if user can modify event"""
        if event.user_id == user_id:
            return True

        participation = self.participant_dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == 'MODERATOR'

    def is_event_owner(self, event: Event, user_id: int) -> bool:
        """Check if user is event owner"""
        return event.user_id == user_id

    def _validate_guest_invitation_data(self, guest_name: str, guest_email: str) -> None:
        errors = []

        if not guest_name or not guest_name.strip():
            errors.append('Guest name is required')
        elif len(guest_name.strip()) < 2:
            errors.append('Guest name must be at least 2 characters long')
        elif len(guest_name.strip()) > 255:
            errors.append('Guest name cannot exceed 255 characters')
        elif not re.match(r'^[a-zA-Z\s\u0100-\u017F\u0400-\u04FF\'.-]+$', guest_name.strip()):
            errors.append('Guest name contains invalid characters')

        if guest_email and guest_email.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, guest_email.strip()):
                errors.append('Guest email format is invalid')
            elif len(guest_email.strip()) > 254:
                errors.append('Guest email cannot exceed 254 characters')

        if errors:
            msg = f'Guest invitation validation failed: {', '.join(errors)}'
            raise EventValidationError(msg)

    def _validate_event_status(self, event: Event) -> None:
        if event.date < timezone.now().date():
            msg = 'Cannot invite guests to past events'
            raise EventValidationError(msg)

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
        """Generate S3 event prefix (folder created lazily on first file upload)"""
        return f'users/{user_uuid}/events/{event_uuid}'

    def _invalidate_caches(
        self,
        event_uuid: str,
        user_id: int,
        event_cache_types: list[str],
        user_cache_types: list[str],
    ) -> None:
        try:
            for cache_type in event_cache_types:
                self.cache_manager.invalidate_event_cache(event_uuid, cache_type)
            for cache_type in user_cache_types:
                self.cache_manager.invalidate_user_cache(user_id, cache_type)
        except Exception as e:
            logger.warning(f'Cache invalidation failed for event {event_uuid}: {e}')
