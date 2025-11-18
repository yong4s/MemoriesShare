from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel


class EventQuerySet(models.QuerySet):
    """Optimized QuerySet for events with annotations"""

    def for_user(self, user_id):
        """Events where user is a participant"""
        return self.filter(participants=user_id).distinct()

    def with_statistics(self):
        """Add participant statistics via annotations"""
        from django.apps import apps

        EventParticipant = apps.get_model('events', 'EventParticipant')
        return self.annotate(
            total_participants=models.Count('participants_through'),
            attending_count=models.Count(
                'participants_through',
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
                'participants_through',
                filter=models.Q(participants_through__rsvp_status=EventParticipant.RsvpStatus.DECLINED),
            ),
            maybe_count=models.Count(
                'participants_through',
                filter=models.Q(
                    participants_through__rsvp_status__in=[
                        EventParticipant.RsvpStatus.MAYBE,
                        EventParticipant.RsvpStatus.TENTATIVE,
                    ]
                ),
            ),
            pending_count=models.Count(
                'participants_through',
                filter=models.Q(participants_through__rsvp_status=EventParticipant.RsvpStatus.PENDING),
            ),
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

    def with_statistics(self):
        return self.get_queryset().with_statistics()

    def upcoming(self):
        return self.get_queryset().upcoming()

    def past(self):
        return self.get_queryset().past()


class Event(BaseModel):
    """
    Clean "dumb" Event model - only defines data structure.
    Business logic moved to EventService, queries optimized in EventQuerySet.
    """

    # Core identification
    event_uuid = models.UUIDField(_('Event UUID'), unique=True, editable=False, db_index=True)

    event_name = models.CharField(_('Event Name'), max_length=255, db_index=True)

    description = models.TextField(_('Description'), blank=True, default='')

    # M2M relationship through EventParticipant
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='events.EventParticipant',
        related_name='joined_events',
        blank=True,
        verbose_name=_('Participants'),
    )

    # Event timing
    date = models.DateField(_('Event Date'), db_index=True)

    time = models.TimeField(_('Event Time'), null=True, blank=True)

    all_day = models.BooleanField(_('All Day Event'), default=False)

    # Location
    location = models.CharField(_('Location'), max_length=255, blank=True)

    address = models.TextField(_('Address'), blank=True)

    # Event settings
    is_public = models.BooleanField(_('Public Event'), default=False)

    # S3 storage
    s3_prefix = models.CharField(
        _('S3 Prefix'), max_length=500, blank=True, help_text=_('S3 folder path for event files')
    )

    objects = EventManager()

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')
        ordering = ['-date', 'event_name']
        indexes = [
            models.Index(fields=['date', 'is_public']),
            models.Index(fields=['event_uuid']),
        ]

    def __str__(self):
        return f'{self.event_name} ({self.date})'

    def clean(self):
        """Basic field validation only"""
        super().clean()
        errors = {}

        if not self.event_name or len(self.event_name.strip()) < 3:
            errors['event_name'] = _('Event name must be at least 3 characters')

        if self.description and len(self.description.strip()) < 3:
            errors['description'] = _('Description must be at least 3 characters')

        # Only restrict past dates for new events, allow editing historical events
        if self._state.adding and self.date and self.date < timezone.now().date():
            errors['date'] = _('Event date cannot be in the past')
            
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Clean data before saving"""
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
