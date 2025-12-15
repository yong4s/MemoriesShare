from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel


class EventParticipantQuerySet(models.QuerySet):
    """Custom QuerySet for event participants"""

    def owners(self):
        """Get only event owners"""
        return self.filter(role=EventParticipant.Role.OWNER)

    def guests(self):
        """Get only event guests"""
        return self.filter(role=EventParticipant.Role.GUEST)

    def moderators(self):
        """Get only event moderators"""
        return self.filter(role=EventParticipant.Role.MODERATOR)

    def accepted(self):
        """Get participants who accepted"""
        return self.filter(rsvp_status=EventParticipant.RsvpStatus.ACCEPTED)

    def declined(self):
        """Get participants who declined"""
        return self.filter(rsvp_status=EventParticipant.RsvpStatus.DECLINED)

    def pending(self):
        """Get participants with pending RSVP"""
        return self.filter(rsvp_status=EventParticipant.RsvpStatus.PENDING)

    def attending(self):
        """Get participants who are attending (various positive statuses)"""
        return self.filter(
            rsvp_status__in=[
                EventParticipant.RsvpStatus.ACCEPTED,
                EventParticipant.RsvpStatus.CONFIRMED_PLUS_ONE,
                EventParticipant.RsvpStatus.TENTATIVE,
                EventParticipant.RsvpStatus.MAYBE,
            ]
        )

    def for_event(self, event):
        """Get participants for specific event"""
        return self.filter(event=event)

    def for_user(self, user):
        """Get participations for specific user"""
        return self.filter(user=user)

    def owners_emails(self):
        """Get list of owner emails for notification sending."""
        return list(self.owners().values_list("user__email", flat=True))

    def active(self):
        """Get active (non-canceled) participants."""
        return self.exclude(rsvp_status=self.model.RsvpStatus.CANCELED)


class EventParticipantManager(models.Manager):
    """Custom manager for event participants"""

    def get_queryset(self):
        return EventParticipantQuerySet(self.model, using=self._db)

    def owners(self):
        return self.get_queryset().owners()

    def guests(self):
        return self.get_queryset().guests()

    def moderators(self):
        return self.get_queryset().moderators()

    def accepted(self):
        return self.get_queryset().accepted()

    def declined(self):
        return self.get_queryset().declined()

    def pending(self):
        return self.get_queryset().pending()

    def attending(self):
        return self.get_queryset().attending()

    def for_event(self, event):
        return self.get_queryset().for_event(event)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class EventParticipant(BaseModel):
    """Through model linking Users to Events with roles and RSVP tracking."""

    class Role(models.TextChoices):
        OWNER = "OWNER", _("Event Owner")
        GUEST = "GUEST", _("Event Guest")
        MODERATOR = "MODERATOR", _("Event Moderator")

    class RsvpStatus(models.TextChoices):
        ACCEPTED = "accepted", _("Accepted")
        DECLINED = "declined", _("Declined")
        PENDING = "pending", _("Pending")
        TENTATIVE = "tentative", _("Tentative")
        CANCELED = "canceled", _("Canceled")
        NO_SHOW = "no_show", _("No Show")
        WAITLISTED = "waitlisted", _("Waitlisted")
        MAYBE = "maybe", _("Maybe")
        CONFIRMED_PLUS_ONE = "confirmed_plus_one", _("Confirmed +1")
        DECLINED_WITH_REGRET = "declined_with_regret", _("Declined with Regret")

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="participants_through",
        verbose_name=_("Event"),
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_participations",
        verbose_name=_("User"),
        db_index=True,
    )

    role = models.CharField(
        _("Role"),
        max_length=10,
        choices=Role.choices,
        default=Role.GUEST,
        db_index=True,
        help_text=_("Role of the user in this event"),
    )

    rsvp_status = models.CharField(
        _("RSVP Status"),
        max_length=20,
        choices=RsvpStatus.choices,
        default=RsvpStatus.PENDING,
        db_index=True,
        help_text=_("Response status to event invitation"),
    )

    guest_name = models.CharField(
        _("Guest Display Name"),
        max_length=255,
        blank=True,
        help_text=_("Display name for guest users in this event"),
    )

    guest_email = models.EmailField(
        _("Guest Contact Email"),
        blank=True,
        null=True,
        help_text=_("Contact email for guest (not for authentication)"),
    )

    guest_phone = models.CharField(
        _("Guest Phone"),
        max_length=15,
        blank=True,
        help_text=_("Phone number in format +XXXXXXXXXX"),
    )

    dietary_preferences = models.TextField(
        _("Dietary Preferences"),
        blank=True,
        help_text=_("Special dietary preferences or restrictions"),
    )

    invitation_sent_at = models.DateTimeField(
        _("Invitation Sent"),
        null=True,
        blank=True,
        help_text=_("Date and time when invitation was sent"),
    )

    responded_at = models.DateTimeField(
        _("Response Date"),
        null=True,
        blank=True,
        help_text=_("Date and time when user responded to invitation"),
    )

    invite_token_used = models.CharField(
        _("Invitation Token Used"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Token used to join this event"),
        db_index=True,
    )

    join_method = models.CharField(
        _("Join Method"),
        max_length=20,
        choices=[
            ("direct", _("Direct Addition")),
            ("invitation", _("Email Invitation")),
            ("qr_code", _("QR Code")),
            ("link", _("Event Link")),
        ],
        default="direct",
        help_text=_("How the participant joined the event"),
    )

    objects = EventParticipantManager()

    class Meta:
        db_table = "events_eventparticipant"
        verbose_name = _("Event Participant")
        verbose_name_plural = _("Event Participants")
        unique_together = ("event", "user")
        ordering = ["event", "role", "user__email"]
        indexes = [
            models.Index(fields=["event", "role"]),
            models.Index(fields=["user", "role"]),
            models.Index(fields=["event", "rsvp_status"]),
            models.Index(fields=["rsvp_status"]),
            models.Index(fields=["invite_token_used"]),
        ]

    def clean(self):
        super().clean()
        if self.user and self.user.is_registered:
            self.guest_name = ""
            self.guest_email = ""
            self.guest_phone = ""

    def save(self, *args, **kwargs):
        if self.guest_name:
            self.guest_name = self.guest_name.strip()
        if self.guest_email:
            self.guest_email = self.guest_email.lower().strip()
        if self.guest_phone:
            self.guest_phone = self.guest_phone.strip()

        if self.user and self.user.is_guest and not self.guest_name:
            self.guest_name = self.user.display_name

        self.clean()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    @property
    def display_name(self) -> str:
        """Get display name for this participant"""
        if self.user.is_registered:
            return self.user.display_name
        else:
            return self.guest_name or self.user.display_name

    @property
    def contact_email(self) -> str:
        """Get contact email for this participant"""
        if self.user.is_registered and self.user.email:
            return self.user.email
        return self.guest_email or ""

    @property
    def has_responded(self) -> bool:
        """Check if participant has responded to invitation"""
        return self.rsvp_status != self.RsvpStatus.PENDING

    @property
    def is_attending(self) -> bool:
        """Check if participant plans to attend"""
        return self.rsvp_status in [
            self.RsvpStatus.ACCEPTED,
            self.RsvpStatus.CONFIRMED_PLUS_ONE,
            self.RsvpStatus.TENTATIVE,
            self.RsvpStatus.MAYBE,
        ]

    @property
    def is_owner(self) -> bool:
        """Check if participant is event owner"""
        return self.role == self.Role.OWNER

    @property
    def is_guest(self) -> bool:
        """Check if participant is event guest"""
        return self.role == self.Role.GUEST

    @property
    def is_moderator(self) -> bool:
        """Check if participant is event moderator"""
        return self.role == self.Role.MODERATOR

    def __str__(self):
        return f"{self.display_name} - {self.get_role_display()} at {self.event.event_name}"

    def __repr__(self):
        return (
            f"<EventParticipant(event='{self.event.event_name}', "
            f"user='{self.user}', role='{self.role}', "
            f"rsvp='{self.rsvp_status}')>"
        )
