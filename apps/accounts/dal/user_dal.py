import logging
from datetime import timedelta

from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models.custom_user import CustomUser
from apps.shared.decorators.database import handle_create_errors
from apps.shared.decorators.database import handle_update_errors

logger = logging.getLogger(__name__)


class UserDAL:
    """Data Access Layer for CustomUser operations"""

    def get_by_id(self, user_id: int) -> CustomUser | None:
        """Get user by ID with optimized query"""
        try:
            return CustomUser.objects.select_related().get(id=user_id)
        except CustomUser.DoesNotExist:
            return None

    def get_by_uuid(self, user_uuid: str) -> CustomUser | None:
        """Get user by UUID"""
        try:
            return CustomUser.objects.select_related().get(user_uuid=user_uuid)
        except CustomUser.DoesNotExist:
            return None

    def get_by_email(self, email: str, registered_only: bool = True) -> CustomUser | None:
        """Get user by email with case-insensitive lookup"""
        if not email:
            return None

        queryset = CustomUser.objects.select_related()
        if registered_only:
            queryset = queryset.filter(is_registered=True)

        try:
            return queryset.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return None

    def get_login_capabilities(self, email: str) -> dict | None:
        """Return login capability flags for an email, or None if no user exists."""
        user = self.get_by_email(email, registered_only=False)
        if user is None:
            return None
        return {
            'has_password': user.has_usable_password(),
            'preferred': user.preferred_login_method,
            'is_active': user.is_active,
        }

    @handle_create_errors(model_name='CustomUser')
    def create_registered_user(
        self,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
        **extra_fields,
    ) -> CustomUser:
        """Create registered user through manager"""
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            is_registered=True,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
        logger.info(f'Created registered user: {email} (ID: {user.id})')
        return user

    @handle_create_errors(model_name='CustomUser')
    def create_guest_user(
        self,
        guest_name: str,
        email: str,
        **extra_fields,
    ) -> CustomUser:
        """Create non-registered email-based user (passwordless/guest)."""
        normalized_email = email.lower().strip()
        if not normalized_email:
            msg = 'Email is required for non-registered users'
            raise ValueError(msg)

        user = CustomUser.objects.create(
            email=normalized_email,
            guest_name=guest_name,
            is_registered=False,
            is_active=True,
            **extra_fields,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        logger.info(f'Created guest user: {guest_name} (ID: {user.id})')
        return user

    @handle_update_errors(model_name='CustomUser')
    def update_user(self, user: CustomUser, **update_fields) -> CustomUser:
        """Update user with given fields"""
        for field, value in update_fields.items():
            setattr(user, field, value)

        user.save(update_fields=list(update_fields.keys()))
        logger.info(f'Updated user {user.id} fields: {list(update_fields.keys())}')
        return user

    def get_registered_users(self, limit: int | None = None) -> QuerySet[CustomUser]:
        """Get registered users queryset"""
        queryset = CustomUser.objects.filter(is_registered=True).select_related()
        if limit:
            queryset = queryset[:limit]
        return queryset

    def get_guest_users(self, limit: int | None = None) -> QuerySet[CustomUser]:
        """Get guest users queryset"""
        queryset = CustomUser.objects.filter(is_registered=False).select_related()
        if limit:
            queryset = queryset[:limit]
        return queryset

    def search_users(self, query: str, registered_only: bool = True) -> QuerySet[CustomUser]:
        """Search users by name or email"""
        if not query:
            return CustomUser.objects.none()

        queryset = CustomUser.objects.select_related()
        if registered_only:
            queryset = queryset.filter(is_registered=True)

        search_filter = (
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(guest_name__icontains=query)
        )

        return queryset.filter(search_filter)

    def cleanup_inactive_guests(self, days_old: int = 30) -> int:
        """Remove old inactive guest users"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days_old)
            inactive_guests = CustomUser.objects.filter(
                is_registered=False, is_active=False, created_at__lt=cutoff_date
            )

            count = inactive_guests.count()
            inactive_guests.delete()

            logger.info(f'Cleaned up {count} inactive guest users')
            return count
        except Exception as e:
            logger.exception(f'Error cleaning up inactive guests: {e}')
            return 0

    def get_user_count(self) -> int:
        """Get total user count"""
        return CustomUser.objects.count()

    def get_registered_user_count(self) -> int:
        """Get registered user count"""
        return CustomUser.objects.filter(is_registered=True).count()

    def get_guest_user_count(self) -> int:
        """Get guest user count"""
        return CustomUser.objects.filter(is_registered=False).count()

    def get_active_user_count(self) -> int:
        """Get active user count"""
        return CustomUser.objects.filter(is_active=True).count()

    def get_inactive_user_count(self) -> int:
        """Get inactive user count"""
        return CustomUser.objects.filter(is_active=False).count()
