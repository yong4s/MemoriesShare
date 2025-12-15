from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser model"""

    def create_user(self, email=None, password=None, **extra_fields):
        """Create and return regular user"""
        # Handle guest users (no email, no password)
        if not email:
            if not extra_fields.get("guest_name"):
                raise ValidationError("Guest users must have a guest_name")
            extra_fields.setdefault("is_registered", False)
            extra_fields.setdefault("is_active", True)

            user = self.model(email=None, **extra_fields)
            user.set_unusable_password()
            user.save(using=self._db)
            return user

        # Handle registered users (email + password required)
        if not email:
            raise ValidationError("Email is required for registered users")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_registered", True)
        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_registered", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def get_registered_users(self):
        """Get queryset of registered users only"""
        return self.filter(is_registered=True)

    def get_guest_users(self):
        """Get queryset of guest users only"""
        return self.filter(is_registered=False)
