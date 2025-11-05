import uuid

from django.db import models
from django.utils import timezone
from datetime import timedelta


class MagicLinkModel(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField()
    is_used = models.BooleanField(default=False)
    expired_at = models.DateTimeField(default=lambda: timezone.now() + timedelta(minutes=15))

    def is_valid(self) -> bool:
        return not self.is_used and self.expired_at < timezone.now()

    def merk_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])

