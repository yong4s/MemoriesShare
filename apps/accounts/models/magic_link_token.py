import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


class MagicLinkModel(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField()
    is_used = models.BooleanField(default=False)
    expired_at = models.DateTimeField(default=lambda: timezone.now() + timedelta(minutes=15))

    def is_valid(self) -> bool:
        is_still_fresh = not self.is_used
        is_not_expired = self.expired_at > timezone.now()

        return is_still_fresh and is_not_expired

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])
