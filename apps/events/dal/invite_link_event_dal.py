from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import F
from django.db.models import Q
from django.utils import timezone

from apps.events.models.invite_link_event import InviteEventLink
from apps.shared.decorators.database import handle_create_errors
from apps.shared.decorators.database import handle_read_errors
from apps.shared.decorators.database import handle_update_errors

if TYPE_CHECKING:
    from datetime import datetime

    from apps.events.models.event import Event


class InviteLinkEventDAL:
    """Data access layer for public event invite links."""

    @handle_create_errors(model_name='InviteEventLink')
    def create_event_invite_link(self, event: Event, expires_at: datetime, max_uses: int) -> InviteEventLink:
        """Create a new invite link for an event."""
        return InviteEventLink.objects.create(event=event, expires_at=expires_at, max_uses=max_uses)

    @handle_read_errors(model_name='InviteEventLink')
    def get_active_invite_link_for_event(self, event: Event) -> InviteEventLink | None:
        """Return the most recent active invite link for the event."""
        return (
            InviteEventLink.objects.filter(event=event)
            .filter(used_count__lt=F('max_uses'))
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .order_by('-created_at')
            .first()
        )

    @handle_read_errors(model_name='InviteEventLink')
    def get_invite_by_token_for_update(self, invite_token: str) -> InviteEventLink:
        """Lock invite link row to guarantee single atomic consume operation."""
        return InviteEventLink.objects.select_related('event').select_for_update().get(invite_token=invite_token)

    @handle_update_errors(model_name='InviteEventLink')
    def increment_used_count(self, invite: InviteEventLink) -> InviteEventLink:
        """Atomically increment usage counter for invite link."""
        InviteEventLink.objects.filter(pk=invite.pk).update(used_count=F('used_count') + 1)
        invite.refresh_from_db(fields=['used_count', 'updated_at'])
        return invite

    @handle_update_errors(model_name='InviteEventLink')
    def revoke_invite(self, invite: InviteEventLink) -> InviteEventLink:
        """Invalidate invite immediately: rotate token + force expiry to now.

        Token rotation guarantees previously-issued signed payloads can no longer
        resolve to this row; expiry close-out makes the invite ineligible for any
        future consume attempts even on signature replay.
        """
        new_token = uuid.uuid4()
        revoked_at = timezone.now()
        InviteEventLink.objects.filter(pk=invite.pk).update(
            invite_token=new_token,
            expires_at=revoked_at,
        )
        invite.refresh_from_db(fields=['invite_token', 'expires_at', 'updated_at'])
        return invite

    @handle_update_errors(model_name='InviteEventLink')
    def extend_invite(
        self,
        invite: InviteEventLink,
        new_expires_at: datetime | None,
        new_max_uses: int | None,
    ) -> InviteEventLink:
        """Extend invite only if new values strictly exceed current ones (never shrink)."""
        update_fields: dict[str, object] = {}
        if new_expires_at is not None and (invite.expires_at is None or new_expires_at > invite.expires_at):
            update_fields['expires_at'] = new_expires_at
        if new_max_uses is not None and new_max_uses > invite.max_uses:
            update_fields['max_uses'] = new_max_uses

        if update_fields:
            InviteEventLink.objects.filter(pk=invite.pk).update(**update_fields)
            invite.refresh_from_db(fields=[*update_fields.keys(), 'updated_at'])
        return invite
