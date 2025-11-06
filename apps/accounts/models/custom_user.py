"""Unified CustomUser model for registered and guest users."""

import uuid
from typing import ClassVar
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.managers.custom_user_manager import CustomUserManager
from apps.shared.base.models import BaseModel


class CustomUser(AbstractUser, BaseModel):
    """Unified User Model for both Guests and Registered Users."""

    username = None
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    # Email is optional (null=True) for guest users
    email = models.EmailField(
        _('email address'),
        unique=True,
        null=True,  # Critical: allows guest users without email
        blank=True,
        help_text=_('Required for registered users, optional for guests'),
    )

    # Core differentiator between user types
    is_registered = models.BooleanField(
        default=False,
        db_index=True,  # Performance: frequent filtering
        help_text=_('True for registered users, False for guests'),
    )

    # UUID for S3 structure and external references
    user_uuid = models.UUIDField(
        _('User UUID'),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text=_('UUID for S3 storage structure and external references'),
    )

    # Guest-specific fields (when is_registered=False)
    guest_name = models.CharField(
        _('Guest Display Name'), max_length=255, blank=True, help_text=_('Display name for guest users in events')
    )

    # Invitation tracking for guests
    invite_token_used = models.CharField(
        _('Used Invitation Token'),
        max_length=64,
        null=True,
        blank=True,
        help_text=_('Token used to create this guest user'),
        db_index=True,
    )

    # User upgrade tracking - when guest becomes registered
    original_guest_data = models.JSONField(
        _('Original Guest Data'), null=True, blank=True, help_text=_('Backup of guest data when user registers')
    )

    # Authentication configuration
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    # Set the custom manager
    objects = CustomUserManager()

    class Meta:
        db_table = 'accounts_customuser'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email', 'is_registered']),
            models.Index(fields=['is_registered', 'is_active']),
            models.Index(fields=['user_uuid']),
            models.Index(fields=['invite_token_used']),
        ]
        constraints = [
            # Ensure registered users have email
            models.CheckConstraint(
                check=models.Q(is_registered=False) | models.Q(email__isnull=False),
                name='registered_users_must_have_email',
            ),
        ]

    def clean(self):
        """Business logic validation"""
        super().clean()
        errors = {}

        # All users with email must have unique email
        if self.email:
            existing_user = CustomUser.objects.filter(email=self.email).exclude(pk=self.pk).first()
            if existing_user:
                errors['email'] = _('A user with this email already exists')

        # NEW LOGIC: is_registered determines password requirements
        if self.is_registered:
            # is_registered=True: Traditional users with password
            if not self.email:
                errors['email'] = _('Email is required for registered users')
            if not self.has_usable_password():
                errors['password'] = _('Password is required for registered users')
            # Clear guest fields for registered users
            if self.guest_name:
                self.guest_name = ''
        else:
            # is_registered=False: Passwordless users OR guests
            if self.email and self.has_usable_password():
                errors['password'] = _('Passwordless users cannot have passwords')
            # If no email, must be guest with guest_name
            if not self.email and not self.guest_name:
                errors['guest_name'] = _('Guest users must have a display name')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save with additional business logic"""
        # Normalize email if provided
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)

        # Clean guest_name and names
        if self.guest_name:
            self.guest_name = self.guest_name.strip()
        if self.first_name:
            self.first_name = self.first_name.strip()
        if self.last_name:
            self.last_name = self.last_name.strip()

        # Ensure guests don't have passwords
        if not self.is_registered and self.has_usable_password():
            self.set_unusable_password()

        # Validate before saving
        self.clean()

        super().save(*args, **kwargs)

    @property
    def is_guest(self) -> bool:
        """Check if user is a guest"""
        return not self.is_registered

    @property
    def display_name(self) -> str:
        """Get display name for UI purposes"""
        if self.is_registered:
            # For registered users, prefer full name, fallback to email
            if self.first_name or self.last_name:
                full_name = f'{self.first_name} {self.last_name}'.strip()
                return full_name if full_name else self.email or f'User {self.id}'
            return self.email or f'User {self.id}'
        else:
            # For guests, use guest_name or fallback
            return self.guest_name or f'Guest {self.id}'

    @property
    def full_name(self) -> str:
        """Get full name (first + last)"""
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return ''

    def convert_to_registered(
        self, email: str, password: str, first_name: str = '', last_name: str = ''
    ) -> 'CustomUser':
        """
        Convert guest user to registered user.

        This method handles the upgrade process while preserving
        all existing relationships and data.
        """
        if self.is_registered:
            raise ValidationError('User is already registered')

        # Check email availability
        if CustomUser.objects.filter(email=email, is_registered=True).exists():
            raise ValidationError('Email already in use by registered user')

        # Backup guest data before conversion
        self.original_guest_data = {
            'guest_name': self.guest_name,
            'invite_token_used': self.invite_token_used,
            'converted_at': timezone.now().isoformat(),
        }

        # Update user fields
        self.email = email
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_registered = True

        # Clear guest-specific fields
        self.guest_name = ''
        self.invite_token_used = None

        self.save()
        return self

    def get_event_participations(self):
        """Get all event participations for this user"""
        return self.event_participations.select_related('event').all()

    def get_owned_events(self):
        """Get events where this user is the owner"""
        from apps.events.models import EventParticipant

        return self.joined_events.filter(eventparticipant__role=EventParticipant.Role.OWNER)

    def get_guest_events(self):
        """Get events where this user is a guest"""
        from apps.events.models import EventParticipant

        return self.joined_events.filter(eventparticipant__role=EventParticipant.Role.GUEST)

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return f"<CustomUser(id={self.id}, email='{self.email}', is_registered={self.is_registered})>"
