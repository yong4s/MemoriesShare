import logging
import uuid
from typing import Any

from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db import IntegrityError
from django.db import transaction

from apps.accounts.services.user_service import UserService
from apps.events.cache.event_cache_invalidator import EventCacheInvalidator
from apps.events.cache.event_cache_service import EventCacheService
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.exceptions import DuplicateParticipantError
from apps.events.exceptions import EventCreationError
from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import OwnerRemovalError
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.events.services.permission_service import EventPermissionService
from apps.events.tasks import cleanup_event_s3_prefix_task
from apps.events.tasks import send_event_invitation_task
from apps.events.validators import EventParticipantValidator
from apps.shared.exceptions import AppError
from apps.shared.utils.redact import redact_secrets

logger = logging.getLogger(__name__)


def build_event_s3_prefix(user_uuid: object, event_uuid: object) -> str:
    """Canonical S3 prefix; all creation paths must build it here."""
    return f'users/{user_uuid}/events/{event_uuid}'


class EventService:
    """Service for event business logic operations"""

    # Constants for pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        dal: EventDAL,
        participant_dal: EventParticipantDAL,
        permission_service: EventPermissionService,
        cache_service: EventCacheService,
        cache_invalidator: EventCacheInvalidator,
        user_service: UserService,
    ):
        self.dal = dal
        self.participant_dal = participant_dal
        self.permission_service = permission_service
        self.cache_service = cache_service
        self.cache_invalidator = cache_invalidator
        self.user_service = user_service
        self._rsvp_validator = EventParticipantValidator()

    @transaction.atomic
    def create_event(self, user, validated_data: dict[str, Any]) -> Event:
        """Create event with lazy S3 folder creation on first file upload"""
        event_uuid = uuid.uuid4()
        s3_prefix = build_event_s3_prefix(user.user_uuid, event_uuid)

        event_data = validated_data.copy()
        event_data['event_uuid'] = event_uuid
        event_data['s3_prefix'] = s3_prefix

        try:
            event = self.dal.create_event(event_data)
            self._add_owner_participation(event, user)
            return event
        except (IntegrityError, DatabaseError) as db_error:
            logger.exception(f'Failed to create event in DB: {db_error}')
            raise EventCreationError(details=str(db_error)) from db_error

    def get_event_detail(self, event_uuid: str, user_id: int) -> Event:
        event_for_authz = self.dal.get_event_by_uuid_with_participants(event_uuid)
        self.permission_service.validate_guest_or_owner_access(event_for_authz, user_id)

        return self.cache_service.get_or_set_event_detail(
            event_uuid=event_uuid,
            fetch_func=lambda: self.dal.get_event_by_uuid_optimized_with_participants(event_uuid),
            timeout=600,  # 10 minutes
        )

    def get_events_list(self, filters: dict[str, Any], user) -> dict[str, Any]:
        page = filters.get('page', 1)
        page_size = min(filters.get('page_size', self.DEFAULT_PAGE_SIZE), self.MAX_PAGE_SIZE)
        search = filters.get('search', '').strip()
        scope = filters.get('scope', 'all')

        if scope == 'owned':
            queryset = self.dal.get_owned_events_queryset(user.id)
        elif scope == 'participating':
            queryset = self.dal.get_participating_events_queryset(user.id)
        elif scope == 'public':
            queryset = self.dal.get_public_events_queryset()
        else:
            queryset = self.dal.get_user_events_queryset(user.id)

        queryset = queryset.search(search).with_statistics_ordered().optimized()

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
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)

        self.permission_service.validate_modify_access(event, user.id)

        updated_event = self.dal.update_event(event, validated_data)

        self.cache_invalidator.invalidate(event_uuid, [user.id], ['detail', 'statistics'])

        return updated_event

    @transaction.atomic
    def delete_event(self, event_uuid: str, user_id: int) -> bool:
        # DAL now raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)

        self.permission_service.validate_owner_access(event, user_id)

        s3_prefix = event.s3_prefix
        result = self.dal.delete_event(event)

        # Heavy I/O moves to Celery — keeps DB locks short and request thread free.
        transaction.on_commit(
            lambda: cleanup_event_s3_prefix_task.delay(s3_prefix, str(event_uuid)),
        )
        self.cache_invalidator.invalidate(event_uuid, [user_id], ['detail', 'statistics', 'participants'])

        return result

    def get_event_participants(
        self,
        event_uuid: str,
        requesting_user_id: int,
        role_filter: str | None = None,
        rsvp_filter: str | None = None,
    ) -> list[EventParticipant]:
        # Check permissions first (not cached)
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)
        self.permission_service.validate_participant_or_owner_access(event, requesting_user_id)

        # Use caching for participants list (with filters as cache key)
        cached_participants = self.cache_service.get_cached_event_participants(event_uuid, role_filter, rsvp_filter)
        if cached_participants is not None:
            return cached_participants

        # Cache miss - fetch from database
        participants = self.participant_dal.get_event_participants(event, role_filter, rsvp_filter)

        # Cache for 3 minutes (participant status can change frequently)
        self.cache_service.cache_event_participants(event_uuid, participants, role_filter, rsvp_filter, timeout=180)

        return participants

    @transaction.atomic
    def add_participant_to_event(
        self,
        event_uuid: str,
        user,
        requesting_user_id: int,
        role: str = EventParticipant.Role.GUEST,
        guest_name: str = '',
        guest_email: str = '',
    ) -> EventParticipant:
        # DAL raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)

        self.permission_service.validate_modify_access(event, requesting_user_id)

        if self.participant_dal.is_user_participant(event, user):
            raise DuplicateParticipantError(user_identifier=str(user.id))

        participation_data = {
            'event': event,
            'user': user,
            'role': role,
            'guest_name': guest_name or user.display_name,
            'guest_email': guest_email or getattr(user, 'email', ''),
            'rsvp_status': EventParticipant.RsvpStatus.PENDING,
        }

        participant = self.participant_dal.create_participant(participation_data)

        logger.info(f'Participant added: user {user.id} as {role} to event {event_uuid}')

        # Skip self-additions (e.g. owner-on-create) — those are not "invites".
        is_self_add = requesting_user_id == user.id
        if not is_self_add:
            participant_pk = participant.pk
            transaction.on_commit(lambda: send_event_invitation_task.delay(participant_pk))

        self.cache_invalidator.invalidate(event_uuid, [user.id], ['detail', 'participants', 'statistics'])

        return participant

    def invite_guest(
        self,
        event_uuid: str,
        guest_name: str,
        guest_email: str,
        requesting_user_id: int,
    ) -> EventParticipant:
        invitee = self._resolve_invitee(guest_name=guest_name, guest_email=guest_email)
        return self.add_participant_to_event(
            event_uuid=event_uuid,
            user=invitee,
            guest_name=guest_name,
            guest_email=guest_email,
            requesting_user_id=requesting_user_id,
        )

    def bulk_invite_guests(
        self,
        event_uuid: str,
        guests: list[dict[str, str]],
        requesting_user_id: int,
    ) -> dict[str, Any]:
        """Per-guest partial failure: one bad invite must not abort the rest."""
        invited: list[EventParticipant] = []
        failed: list[dict[str, str]] = []
        for guest in guests:
            try:
                invited.append(
                    self.invite_guest(
                        event_uuid=event_uuid,
                        guest_name=guest['guest_name'],
                        guest_email=guest['guest_email'],
                        requesting_user_id=requesting_user_id,
                    )
                )
            except AppError as exc:
                error_code = getattr(exc, 'error_code', type(exc).__name__)
                failed.append({'guest_name': guest['guest_name'], 'error_code': error_code})
                logger.warning(
                    'Guest invitation failed for %s: code=%s detail=%s',
                    guest['guest_name'],
                    error_code,
                    redact_secrets(str(exc)),
                )
        return {'invited': invited, 'failed': failed}

    def _resolve_invitee(self, guest_name: str, guest_email: str):
        existing = self.user_service.get_user_by_email(guest_email, registered_only=False)
        if existing:
            return existing
        return self.user_service.create_guest_user(guest_name=guest_name, guest_email=guest_email)

    @transaction.atomic
    def remove_participant_from_event(self, event_uuid: str, user, requesting_user_id: int) -> bool:
        # DAL raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)

        if not self.permission_service.can_user_modify_event(event, requesting_user_id):
            msg = 'You cannot remove participants from this event'
            raise EventPermissionError(msg)

        if self.permission_service.is_event_owner(event, user.id):
            raise OwnerRemovalError()

        participation = self.participant_dal.get_user_participation(event, user)
        result = self.participant_dal.remove_participant(participation)

        logger.info(f'Participant removed: user {user.id} from event {event_uuid}')

        self.cache_invalidator.invalidate(
            event_uuid, [requesting_user_id, user.id], ['detail', 'participants', 'statistics']
        )

        return result

    @transaction.atomic
    def update_participant_rsvp(
        self, event_uuid: str, user, rsvp_status: str, requesting_user_id: int
    ) -> EventParticipant:
        # DAL raises EventNotFoundError if event doesn't exist
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)

        participation = self.participant_dal.get_user_participation(event, user)

        if requesting_user_id != user.id and not self.permission_service.can_user_modify_event(
            event, requesting_user_id
        ):
            msg = 'You can only update your own RSVP status'
            raise EventPermissionError(msg)

        self._rsvp_validator.validate_rsvp_change(participation, rsvp_status)

        updated_participant = self.participant_dal.update_participant_rsvp(participation, rsvp_status)

        logger.info(f'RSVP updated: user {user.id} -> {rsvp_status} for event {event_uuid}')

        self.cache_invalidator.invalidate(
            event_uuid, [user.id, requesting_user_id], ['detail', 'participants', 'statistics']
        )

        return updated_participant

    def get_participant_detail(self, event_uuid: str, participant_id: int, requesting_user_id: int) -> EventParticipant:
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)
        self.permission_service.validate_participant_or_owner_access(event, requesting_user_id)
        return self.participant_dal.get_participant_by_pk(event, participant_id)

    def update_participant_rsvp_by_id(
        self, event_uuid: str, participant_id: int, rsvp_status: str, requesting_user_id: int
    ) -> EventParticipant:
        event = self.dal.get_event_by_uuid_with_participants(event_uuid)
        participant = self.participant_dal.get_participant_by_pk(event, participant_id)
        return self.update_participant_rsvp(
            event_uuid=event_uuid,
            user=participant.user,
            rsvp_status=rsvp_status,
            requesting_user_id=requesting_user_id,
        )

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
