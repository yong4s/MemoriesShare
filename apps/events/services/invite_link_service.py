from __future__ import annotations

import logging
import secrets
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from urllib.parse import urlparse

from django.conf import settings
from django.core import signing
from django.core.signing import BadSignature
from django.core.signing import SignatureExpired
from django.db import transaction
from django.utils import timezone

from apps.accounts.dal.user_dal import UserDAL
from apps.events.cache.event_cache_invalidator import EventCacheInvalidator
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.dal.invite_link_event_dal import InviteLinkEventDAL
from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import InviteExpiredError
from apps.events.exceptions import InviteLimitReachedError
from apps.events.models.event_participant import EventParticipant
from apps.events.services.permission_service import EventPermissionService
from apps.shared.exceptions import ResourceNotFoundError
from apps.shared.exceptions import ValidationError
from apps.shared.utils.ngrok import get_ngrok_public_url

if TYPE_CHECKING:
    from apps.accounts.models.custom_user import CustomUser
    from apps.events.models.event import Event
    from apps.events.models.invite_link_event import InviteEventLink


logger = logging.getLogger(__name__)


class InviteLinkService:
    """Business logic for issuing and consuming public event invite links."""

    TOKEN_SALT = 'events.public_invite.v1'
    DEFAULT_TTL_HOURS = 24
    DEFAULT_MAX_USES = 10_000
    MAX_ALLOWED_TTL_HOURS = 168
    MAX_ALLOWED_USES = 100_000

    INVITE_CACHE_TYPES = ['detail', 'participants', 'statistics']

    def __init__(
        self,
        dal: InviteLinkEventDAL,
        event_dal: EventDAL,
        participant_dal: EventParticipantDAL,
        user_dal: UserDAL,
        permission_service: EventPermissionService,
        cache_invalidator: EventCacheInvalidator,
    ) -> None:
        self.dal = dal
        self.event_dal = event_dal
        self.participant_dal = participant_dal
        self.user_dal = user_dal
        self.permission_service = permission_service
        self.cache_invalidator = cache_invalidator

    @transaction.atomic
    def issue_public_invite_link(
        self,
        event_uuid: str,
        requested_by_user_id: int,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        max_uses: int = DEFAULT_MAX_USES,
    ) -> dict[str, str]:
        """Create a signed public invite URL for the event.

        Atomic + row-level lock on the event prevents two concurrent issues from
        each creating a parallel active invite (single-active-invite invariant).
        """
        self._validate_issue_params(ttl_hours=ttl_hours, max_uses=max_uses)
        event = self._resolve_event_for_issue(event_uuid=event_uuid, requested_by_user_id=requested_by_user_id)
        invite = self.dal.get_active_invite_link_for_event(event=event)
        reused = invite is not None
        if invite:
            invite = self.dal.extend_invite(
                invite=invite,
                new_expires_at=self._build_expiration_datetime(ttl_hours=ttl_hours),
                new_max_uses=max_uses,
            )
        else:
            expires_at = self._build_expiration_datetime(ttl_hours=ttl_hours)
            invite = self.dal.create_event_invite_link(
                event=event,
                expires_at=expires_at,
                max_uses=max_uses,
            )

        signed_token = self._sign_invite_payload(
            event_uuid=str(event.event_uuid),
            invite_token=str(invite.invite_token),
            expires_at=self._resolve_token_expiration(invite=invite, ttl_hours=ttl_hours),
        )
        invite_url = self._build_invite_url(signed_token=signed_token)

        return {
            'invite_url': invite_url,
            'reused': reused,
            'max_uses': invite.max_uses,
            'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
        }

    @transaction.atomic
    def revoke_public_invite_link(self, event_uuid: str, requested_by_user_id: int) -> None:
        """Immediately invalidate the active public invite link for an event.

        Locks the event row to serialize against concurrent issue/extend operations,
        then rotates the invite token and forces expiry on the active invite (if any).
        Raises ResourceNotFoundError when the event has no active invite to revoke.
        """
        event = self._resolve_event_for_issue(
            event_uuid=event_uuid,
            requested_by_user_id=requested_by_user_id,
        )
        invite = self.dal.get_active_invite_link_for_event(event=event)
        if invite is None:
            msg = 'No active invite link to revoke for this event'
            raise ResourceNotFoundError(msg, error_code='invite_link_not_found')

        self.dal.revoke_invite(invite=invite)
        self.cache_invalidator.invalidate(event.event_uuid, [requested_by_user_id], self.INVITE_CACHE_TYPES)

    @transaction.atomic
    def consume_public_invite_link(
        self,
        signed_token: str,
        authenticated_user_id: int,
    ) -> dict[str, str | int | bool]:
        """Validate signed token and join event for authenticated user."""
        invite = self._resolve_locked_invite(signed_token=signed_token)
        authenticated_user = self._resolve_authenticated_user(authenticated_user_id=authenticated_user_id)
        existing_participant = self.participant_dal.get_user_participation_by_id(
            event=invite.event,
            user_id=authenticated_user.id,
        )
        if existing_participant:
            return self._build_join_response(
                event=invite.event,
                participant_id=existing_participant.id,
                participant_name=existing_participant.display_name,
                already_joined=True,
            )

        self._ensure_invite_has_capacity(invite=invite)
        participant = self._create_participant_from_invite(invite=invite, authenticated_user=authenticated_user)
        self.dal.increment_used_count(invite=invite)
        self.cache_invalidator.invalidate(
            invite.event.event_uuid, [authenticated_user.id], self.INVITE_CACHE_TYPES
        )
        return self._build_join_response(
            event=invite.event,
            participant_id=participant.id,
            participant_name=authenticated_user.display_name,
            already_joined=False,
        )

    def _validate_issue_params(self, ttl_hours: int, max_uses: int) -> None:
        if ttl_hours < 1 or ttl_hours > self.MAX_ALLOWED_TTL_HOURS:
            msg = f'ttl_hours must be between 1 and {self.MAX_ALLOWED_TTL_HOURS}'
            raise ValidationError(msg, error_code='invite_ttl_invalid')

        if max_uses < 1 or max_uses > self.MAX_ALLOWED_USES:
            msg = f'max_uses must be between 1 and {self.MAX_ALLOWED_USES}'
            raise ValidationError(msg, error_code='invite_max_uses_invalid')

    def _resolve_event_for_issue(self, event_uuid: str, requested_by_user_id: int) -> Event:
        # Locks the event row for the surrounding @transaction.atomic so concurrent
        # issuance attempts serialize and the "single active invite" invariant holds.
        event = self.event_dal.get_event_by_uuid_with_participants_for_update(event_uuid)
        if not self.permission_service.can_user_modify_event(event, requested_by_user_id):
            raise EventPermissionError(action='modify', event_id=str(event.event_uuid))
        return event

    @staticmethod
    def _build_expiration_datetime(ttl_hours: int) -> datetime:
        return timezone.now() + timedelta(hours=ttl_hours)

    @staticmethod
    def _resolve_token_expiration(invite: InviteEventLink, ttl_hours: int) -> datetime:
        if invite.expires_at:
            return invite.expires_at
        return timezone.now() + timedelta(hours=ttl_hours)

    def _resolve_locked_invite(self, signed_token: str) -> InviteEventLink:
        payload = self._decode_invite_payload(signed_token=signed_token)
        invite = self.dal.get_invite_by_token_for_update(invite_token=payload['invite_token'])
        if str(invite.event.event_uuid) != payload['event_uuid']:
            msg = 'Invalid invitation token'
            raise ValidationError(msg, error_code='invite_token_invalid')
        self._ensure_invite_not_expired(invite)
        return invite

    @staticmethod
    def _ensure_invite_not_expired(invite: InviteEventLink) -> None:
        if invite.expires_at and timezone.now() > invite.expires_at:
            raise InviteExpiredError()

    def _resolve_authenticated_user(self, authenticated_user_id: int) -> CustomUser:
        authenticated_user = self.user_dal.get_by_id(authenticated_user_id)
        if not authenticated_user:
            msg = 'Authenticated user not found'
            raise ValidationError(msg, error_code='invite_user_not_found')

        if not authenticated_user.email:
            msg = 'Email-based account is required to join via invite link'
            raise ValidationError(msg, error_code='invite_email_required')

        return authenticated_user

    @staticmethod
    def _ensure_invite_has_capacity(invite: InviteEventLink) -> None:
        if invite.used_count >= invite.max_uses:
            raise InviteLimitReachedError()

    def _create_participant_from_invite(
        self,
        invite: InviteEventLink,
        authenticated_user: CustomUser,
    ) -> EventParticipant:
        return self.participant_dal.create_participant({
            'event': invite.event,
            'user': authenticated_user,
            'role': EventParticipant.Role.GUEST,
            'rsvp_status': EventParticipant.RsvpStatus.PENDING,
            'guest_name': authenticated_user.display_name,
            'guest_email': authenticated_user.email,
            'invite_token_used': str(invite.invite_token),
            'join_method': 'link',
        })

    @staticmethod
    def _build_join_response(
        event: Event,
        participant_id: int,
        participant_name: str,
        already_joined: bool,
    ) -> dict[str, str | int | bool]:
        return {
            'event_uuid': str(event.event_uuid),
            'event_name': event.event_name,
            'participant_id': participant_id,
            'participant_name': participant_name,
            'already_joined': already_joined,
        }

    def _sign_invite_payload(self, event_uuid: str, invite_token: str, expires_at: datetime) -> str:
        payload = {
            'event_uuid': event_uuid,
            'invite_token': invite_token,
            'nonce': secrets.token_urlsafe(12),
            'exp': int(expires_at.timestamp()),
        }
        return signing.dumps(payload, salt=self.TOKEN_SALT)

    def _decode_invite_payload(self, signed_token: str) -> dict[str, str]:
        try:
            raw_payload = signing.loads(
                signed_token,
                salt=self.TOKEN_SALT,
                max_age=self.MAX_ALLOWED_TTL_HOURS * 3600,
            )
        except SignatureExpired as exc:
            raise InviteExpiredError() from exc
        except BadSignature as exc:
            msg = 'Invalid invitation token signature'
            raise ValidationError(msg, error_code='invite_token_invalid_signature') from exc

        if not isinstance(raw_payload, dict):
            msg = 'Invalid invitation payload'
            raise ValidationError(msg, error_code='invite_payload_invalid')

        event_uuid = str(raw_payload.get('event_uuid', '')).strip()
        invite_token = str(raw_payload.get('invite_token', '')).strip()
        exp = raw_payload.get('exp')

        if not event_uuid or not invite_token or not isinstance(exp, int):
            msg = 'Invitation payload is malformed'
            raise ValidationError(msg, error_code='invite_payload_malformed')

        if timezone.now().timestamp() >= exp:
            raise InviteExpiredError()

        return {
            'event_uuid': event_uuid,
            'invite_token': invite_token,
        }

    def _build_invite_url(self, signed_token: str) -> str:
        frontend_base_raw = self._resolve_frontend_base_url()
        parsed_frontend_url = urlparse(frontend_base_raw)
        if (
            not frontend_base_raw
            or parsed_frontend_url.scheme not in {'http', 'https'}
            or not parsed_frontend_url.netloc
        ):
            msg = 'FRONTEND_URL must be a valid absolute URL with http/https scheme'
            raise ValidationError(msg, error_code='invite_frontend_url_invalid')

        frontend_base = frontend_base_raw.rstrip('/')
        invite_path = str(getattr(settings, 'EVENT_INVITE_JOIN_PATH', '/join')).strip() or '/join'
        if not invite_path.startswith('/'):
            invite_path = f'/{invite_path}'

        query = urlencode({'token': signed_token})
        return f'{frontend_base}{invite_path}?{query}'

    @staticmethod
    def _resolve_frontend_base_url() -> str:
        """Resolve frontend URL, preferring ngrok in development."""
        environment = getattr(settings, 'ENVIRONMENT', '')
        if environment == 'development':
            ngrok_url = get_ngrok_public_url()
            if ngrok_url:
                return ngrok_url
        return str(getattr(settings, 'FRONTEND_URL', '')).strip()
