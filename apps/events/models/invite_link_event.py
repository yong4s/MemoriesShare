import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel

from .event import Event


class InviteEventLink(BaseModel):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
        db_index=True,
    )
    invite_token = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        verbose_name=_("Invite Token"),
        help_text=_("Unique token for invitation link"),
    )
    max_uses = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Maximum Uses"),
        help_text=_("Maximum number of times this link can be used"),
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Used Count"),
        help_text=_("Number of times this link has been used"),
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text=_("When this invitation link expires"),
        db_index=True,
    )

    class Meta:
        verbose_name = _("Invite Event Link")
        verbose_name_plural = _("Invite Event Links")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "expires_at"]),
            models.Index(fields=["invite_token"]),
            models.Index(fields=["expires_at", "used_count"]),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.expires_at and self.expires_at <= timezone.now():
            errors["expires_at"] = _("Expiry date must be in the future")

        if self.max_uses < 1:
            errors["max_uses"] = _("Maximum uses must be at least 1")

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Invite link for {self.event.event_name} (expires: {self.expires_at})"

    @property
    def is_active(self):
        now = timezone.now()
        if self.expires_at and now > self.expires_at:
            return False
        if self.used_count >= self.max_uses:
            return False
        return True
