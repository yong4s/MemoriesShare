from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser model"""

    def create_user(self, email=None, password=None, **extra_fields):
        """Create and return a user. Email is required."""
        if not email:
            msg = 'Email is required for all users'
            raise ValidationError(msg)

        email = self.normalize_email(email)
        extra_fields.setdefault('is_registered', bool(password))
        extra_fields.setdefault('is_active', True)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_registered', True)

        if extra_fields.get('is_staff') is not True:
            msg = 'Superuser must have is_staff=True.'
            raise ValueError(msg)
        if extra_fields.get('is_superuser') is not True:
            msg = 'Superuser must have is_superuser=True.'
            raise ValueError(msg)

        return self.create_user(email, password, **extra_fields)
