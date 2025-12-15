import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel


class EventQuerySet(models.QuerySet):
    """Optimized QuerySet for events with annotations and filtering"""

    def for_user(self, user_id):
        """Events where user is a participant"""
        return self.filter(participants=user_id).distinct()

    def for_owner(self, user_id):
        """Events owned by specific user"""
        return self.filter(user_id=user_id)

    def accessible_to_user(self, user_id):
        """All events accessible to user (owned, participating, or public)"""
        return self.filter(
            models.Q(user_id=user_id)  # Own events
            | models.Q(participants=user_id)  # Participant in other events
            | models.Q(is_public=True)  # Public events
        ).distinct()

    def search(self, search_term):
        """Apply search filter to events"""
        if not search_term:
            return self
        return self.filter(
            models.Q(event_name__icontains=search_term)
            | models.Q(description__icontains=search_term)
        )

    def with_statistics(self):
        """Add participant statistics via annotations"""
        from django.apps import apps

        EventParticipant = apps.get_model("events", "EventParticipant")
        return self.annotate(
            total_participants=models.Count("participants_through"),
            attending_count=models.Count(
                "participants_through",
                filter=models.Q(
                    participants_through__rsvp_status__in=[
                        EventParticipant.RsvpStatus.ACCEPTED,
                        EventParticipant.RsvpStatus.CONFIRMED_PLUS_ONE,
                        EventParticipant.RsvpStatus.TENTATIVE,
                        EventParticipant.RsvpStatus.MAYBE,
                    ]
                ),
            ),
            not_attending_count=models.Count(
                "participants_through",
                filter=models.Q(
                    participants_through__rsvp_status=EventParticipant.RsvpStatus.DECLINED
                ),
            ),
            maybe_count=models.Count(
                "participants_through",
                filter=models.Q(
                    participants_through__rsvp_status__in=[
                        EventParticipant.RsvpStatus.MAYBE,
                        EventParticipant.RsvpStatus.TENTATIVE,
                    ]
                ),
            ),
            pending_count=models.Count(
                "participants_through",
                filter=models.Q(
                    participants_through__rsvp_status=EventParticipant.RsvpStatus.PENDING
                ),
            ),
        )

    def with_statistics_ordered(self):
        """Add statistics and default ordering"""
        return self.with_statistics().order_by("-created_at")

    def optimized(self):
        """Apply standard optimizations for event queries"""
        return self.select_related("user").prefetch_related(
            "participants_through__user"
        )

    def upcoming(self):
        """Future events"""
        return self.filter(date__gte=timezone.now().date())

    def past(self):
        """Past events"""
        return self.filter(date__lt=timezone.now().date())


class EventManager(models.Manager):
    """Custom manager for events"""

    def get_queryset(self):
        return EventQuerySet(self.model, using=self._db)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_owner(self, user_id):
        return self.get_queryset().for_owner(user_id)

    def accessible_to_user(self, user_id):
        return self.get_queryset().accessible_to_user(user_id)

    def search(self, search_term):
        return self.get_queryset().search(search_term)

    def with_statistics(self):
        return self.get_queryset().with_statistics()

    def with_statistics_ordered(self):
        return self.get_queryset().with_statistics_ordered()

    def optimized(self):
        return self.get_queryset().optimized()

    def upcoming(self):
        return self.get_queryset().upcoming()

    def past(self):
        return self.get_queryset().past()


class Event(BaseModel):
    """
    Clean "dumb" Event model - only defines data structure.
    Business logic moved to EventService, queries optimized in EventQuerySet.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_events",
        verbose_name=_("Event Owner"),
        db_index=True,
    )

    event_uuid = models.UUIDField(
        _("Event UUID"), unique=True, editable=False, db_index=True
    )

    event_name = models.CharField(_("Event Name"), max_length=255, db_index=True)

    description = models.TextField(_("Description"), blank=True, default="")

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="events.EventParticipant",
        related_name="joined_events",
        blank=True,
        verbose_name=_("Participants"),
    )

    date = models.DateField(_("Event Date"), db_index=True)

    time = models.TimeField(_("Event Time"), null=True, blank=True)

    all_day = models.BooleanField(_("All Day Event"), default=False)

    location = models.CharField(_("Location"), max_length=255, blank=True)

    address = models.TextField(_("Address"), blank=True)

    is_public = models.BooleanField(_("Public Event"), default=False)

    s3_prefix = models.CharField(
        _("S3 Prefix"),
        max_length=500,
        blank=True,
        help_text=_("S3 folder path for event files"),
    )

    objects = EventManager()

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["-date", "event_name"]
        indexes = [
            models.Index(fields=["date", "is_public"]),
            models.Index(fields=["event_uuid"]),
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "is_public"]),
        ]

    def __str__(self):
        return f"{self.event_name} ({self.date})"

    def clean(self):
        """Minimal validation for critical business rules only"""
        super().clean()
        errors = {}

        if self._state.adding and self.date and self.date < timezone.now().date():
            errors["date"] = _("Event date cannot be in the past")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Clean data and auto-generate UUID and S3 prefix"""
        if not self.event_uuid:
            self.event_uuid = uuid.uuid4()

        if not self.s3_prefix and self.event_uuid:
            if self.user_id and hasattr(self.user, "user_uuid"):
                self.s3_prefix = f"users/{self.user.user_uuid}/events/{self.event_uuid}"
            else:
                self.s3_prefix = f"events/{self.event_uuid}"

        if self.event_name:
            self.event_name = self.event_name.strip()
        if self.description:
            self.description = self.description.strip()
        if self.location:
            self.location = self.location.strip()
        if self.address:
            self.address = self.address.strip()

        self.clean()
        super().save(*args, **kwargs)
