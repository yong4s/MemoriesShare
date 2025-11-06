from .custom_user_manager import CustomUserManager

# Re-export old manager for backward compatibility
try:
    from django.contrib.auth.models import BaseUserManager

    class UserManager(BaseUserManager):
        """Legacy UserManager for migration compatibility"""

        use_in_migrations = True

        def create_user(self, email, password=None, **extra_fields):
            if not email:
                raise ValueError('Users must have an email address')

            user = self.model(email=self.normalize_email(email), **extra_fields)
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save(using=self._db)
            return user

        def create_superuser(self, email, password, **extra_fields):
            user = self.create_user(email, password=password, **extra_fields)
            user.is_staff = True
            user.is_superuser = True
            user.save(using=self._db)
            return user

except ImportError:
    UserManager = CustomUserManager

__all__ = ['CustomUserManager', 'UserManager']
