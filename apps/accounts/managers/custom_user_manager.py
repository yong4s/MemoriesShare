"""
CustomUserManager for Unified User Model

Handles creation and querying of both registered users and guest users
through a single manager with specialized methods for each user type.
"""

from typing import Optional

from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.db import transaction


class CustomUserManager(BaseUserManager):
    """
    Custom manager for unified user model with new authentication logic.

    User Types:
    - is_registered=True: Traditional users with email + password
    - is_registered=False: Passwordless users (magic link) OR guest users

    Provides specialized methods for:
    - Creating registered users with email/password (traditional auth)
    - Creating passwordless users with email only (magic link auth)
    - Creating guest users without email/password (event participation)
    - Converting between user types
    - Querying by user type
    """

    use_in_migrations = True

    def normalize_email(self, email):
        """Normalize email address (lowercase domain)"""
        if email:
            return super().normalize_email(email).lower()
        return email

    def create_user(
        self, email: str | None = None, password: str | None = None, is_registered: bool = True, **extra_fields
    ):
        """
        Create user with new is_registered logic.

        Args:
            email: User email (required for registered users)
            password: User password (required for registered users, forbidden for passwordless)
            is_registered: True=traditional auth, False=passwordless/guest
            **extra_fields: Additional user fields

        Returns:
            CustomUser instance

        Raises:
            ValueError: If required fields are missing or invalid combination
            ValidationError: If validation fails
        """
        # NEW LOGIC: is_registered=True requires email and password
        if is_registered:
            if not email:
                raise ValueError('Registered users must have an email address')
            if not password:
                raise ValueError('Registered users must have a password')

        # NEW LOGIC: is_registered=False means passwordless or guest
        elif password:
            raise ValueError('Passwordless users cannot have passwords')
            # Guest users (no email) must have guest_name, but that's validated in model.clean()

        # Normalize email if provided
        if email:
            email = self.normalize_email(email)

        # Set default values
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_registered', is_registered)

        # Create user instance
        user = self.model(email=email, **extra_fields)

        # Set password based on is_registered flag
        if is_registered and password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        # Validate and save
        user.full_clean()  # Trigger model validation
        user.save(using=self._db)

        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """
        Create superuser (always registered).

        Args:
            email: Superuser email
            password: Superuser password
            **extra_fields: Additional fields

        Returns:
            CustomUser instance with superuser privileges
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_registered', True)

        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)

    def create_passwordless_user(self, email: str, **extra_fields) -> 'CustomUser':
        """
        Create passwordless user for magic link authentication.

        Args:
            email: User email (required)
            **extra_fields: Additional fields

        Returns:
            CustomUser instance configured for passwordless auth

        Raises:
            ValueError: If email is missing
        """
        if not email:
            raise ValueError('Passwordless users must have an email address')

        extra_fields.setdefault('is_active', True)

        return self.create_user(email=email, password=None, is_registered=False, **extra_fields)

    @transaction.atomic
    def create_guest_user(self, guest_name: str, invite_token: str | None = None, **extra_fields) -> 'CustomUser':
        """
        Create guest user for event participation.

        Args:
            guest_name: Display name for the guest
            invite_token: Optional invitation token used
            **extra_fields: Additional fields

        Returns:
            CustomUser instance configured as guest
        """
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('guest_name', guest_name)

        if invite_token:
            extra_fields.setdefault('invite_token_used', invite_token)

        return self.create_user(email=None, password=None, is_registered=False, **extra_fields)

    @transaction.atomic
    def create_guest_from_invite(
        self, invite_token: str, guest_name: str, guest_email: str | None = None
    ) -> 'CustomUser':
        """
        Create guest user from invitation token.

        Args:
            invite_token: The invitation token
            guest_name: Guest display name
            guest_email: Optional guest email

        Returns:
            CustomUser instance for guest
        """
        return self.create_guest_user(
            guest_name=guest_name,
            invite_token=invite_token,
        )

    def registered_users(self):
        """Get queryset of traditional users with passwords (is_registered=True)"""
        return self.filter(is_registered=True)

    def passwordless_users(self):
        """Get queryset of passwordless users with email (is_registered=False, email exists)"""
        return self.filter(is_registered=False, email__isnull=False)

    def guest_users(self):
        """Get queryset of guest users without email (is_registered=False, no email)"""
        return self.filter(is_registered=False, email__isnull=True)

    def all_non_registered_users(self):
        """Get queryset of all passwordless + guest users (is_registered=False)"""
        return self.filter(is_registered=False)

    def active_users(self):
        """Get queryset of active users (all types)"""
        return self.filter(is_active=True)

    def active_registered_users(self):
        """Get queryset of active traditional users"""
        return self.filter(is_registered=True, is_active=True)

    def active_passwordless_users(self):
        """Get queryset of active passwordless users"""
        return self.filter(is_registered=False, is_active=True, email__isnull=False)

    def active_guest_users(self):
        """Get queryset of active guest users"""
        return self.filter(is_registered=False, is_active=True, email__isnull=True)

    def users_by_email(self, email: str):
        """
        Get users by email (handles case-insensitive lookup).

        Note: Multiple users can have the same email if one is guest
        and the email is in guest_email field vs main email field.
        """
        if not email:
            return self.none()

        email = self.normalize_email(email)
        return self.filter(email__iexact=email)

    def get_by_email(self, email: str, registered_only: bool = True):
        """
        Get single user by email.

        Args:
            email: Email to search for
            registered_only: If True, only search registered users

        Returns:
            CustomUser instance or None
        """
        queryset = self.users_by_email(email)

        if registered_only:
            queryset = queryset.filter(is_registered=True)

        return queryset.first()

    def get_by_invite_token(self, invite_token: str):
        """Get guest user by invitation token used"""
        if not invite_token:
            return None

        try:
            return self.get(invite_token_used=invite_token, is_registered=False)
        except self.model.DoesNotExist:
            return None

    def get_by_natural_key(self, username):
        """
        Get user by natural key (email).
        Required by Django auth system.
        """
        if not username:
            raise self.model.DoesNotExist()

        # For registered users, use email
        return self.get(email__iexact=username, is_registered=True)

    def cleanup_inactive_guests(self, days_old: int = 30):
        """
        Clean up old inactive guest users.

        Args:
            days_old: Remove guests older than this many days

        Returns:
            Number of users deleted
        """
        from django.utils import timezone

        cutoff_date = timezone.now() - timezone.timedelta(days=days_old)

        old_guests = self.filter(is_registered=False, is_active=False, created_at__lt=cutoff_date)

        count = old_guests.count()
        old_guests.delete()

        return count

    def convert_guest_to_registered(
        self, guest_user: 'CustomUser', email: str, password: str, first_name: str = '', last_name: str = ''
    ) -> 'CustomUser':
        """
        Convert existing guest user to registered user.

        This method preserves all existing relationships and data.
        """
        if guest_user.is_registered:
            raise ValidationError('User is already registered')

        return guest_user.convert_to_registered(email, password, first_name, last_name)
