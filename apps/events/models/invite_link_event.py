from django.db import models
import uuid
from django.utils import timezone

from .event import Event


class InviteEventLink(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE
    )
    invite_token = models.UUIDField(
        unique=True,
        default=uuid.uuid4
    )
    max_uses = models.PositiveIntegerField(
        default=1
    )
    used_count = models.PositiveIntegerField(
        default=0
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def is_active(self):
        now = timezone.now()
        if self.expires_at and now > self.expires_at:
            return False
        if self.used_count >= self.max_uses:
            return False
        return True
