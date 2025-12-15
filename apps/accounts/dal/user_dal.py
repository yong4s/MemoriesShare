import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count
from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models.custom_user import CustomUser

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

    def get_by_email(
        self, email: str, registered_only: bool = True
    ) -> CustomUser | None:
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

    def get_by_invite_token(self, invite_token: str) -> CustomUser | None:
        """Get guest user by invitation token"""
        if not invite_token:
            return None

        try:
            return CustomUser.objects.select_related().get(
                invite_token_used=invite_token, is_registered=False
            )
        except CustomUser.DoesNotExist:
            return None

    def create_registered_user(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **extra_fields,
    ) -> CustomUser:
        """Create registered user through manager"""
        try:
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                is_registered=True,
                first_name=first_name,
                last_name=last_name,
                **extra_fields,
            )
            logger.info(f"Created registered user: {email} (ID: {user.id})")
            return user
        except IntegrityError as e:
            logger.error(f"Integrity error creating user: {e}")
            raise

    def create_guest_user(
        self, guest_name: str, invite_token: str = None, **extra_fields
    ) -> CustomUser:
        """Create guest user"""
        try:
            user = CustomUser.objects.create(
                guest_name=guest_name,
                invite_token_used=invite_token,
                is_registered=False,
                is_active=True,
                **extra_fields,
            )
            user.set_unusable_password()
            user.save()

            logger.info(f"Created guest user: {guest_name} (ID: {user.id})")
            return user
        except Exception as e:
            logger.error(f"Error creating guest user: {e}")
            raise

    def update_user(self, user: CustomUser, **update_fields) -> CustomUser:
        """Update user with given fields"""
        try:
            for field, value in update_fields.items():
                setattr(user, field, value)

            user.save(update_fields=list(update_fields.keys()))
            logger.info(f"Updated user {user.id} fields: {list(update_fields.keys())}")
            return user
        except Exception as e:
            logger.error(f"Error updating user {user.id}: {e}")
            raise

    def get_registered_users(self, limit: int = None) -> QuerySet[CustomUser]:
        """Get registered users queryset"""
        queryset = CustomUser.objects.filter(is_registered=True).select_related()
        if limit:
            queryset = queryset[:limit]
        return queryset

    def get_guest_users(self, limit: int = None) -> QuerySet[CustomUser]:
        """Get guest users queryset"""
        queryset = CustomUser.objects.filter(is_registered=False).select_related()
        if limit:
            queryset = queryset[:limit]
        return queryset

    def search_users(
        self, query: str, registered_only: bool = True
    ) -> QuerySet[CustomUser]:
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

    def get_active_users(self) -> QuerySet[CustomUser]:
        """Get active users"""
        return CustomUser.objects.filter(is_active=True).select_related()

    def get_inactive_users(self) -> QuerySet[CustomUser]:
        """Get inactive users"""
        return CustomUser.objects.filter(is_active=False).select_related()

    def cleanup_inactive_guests(self, days_old: int = 30) -> int:
        """Remove old inactive guest users"""
        try:
            cutoff_date = timezone.now() - timedelta(days=days_old)
            inactive_guests = CustomUser.objects.filter(
                is_registered=False, is_active=False, created_at__lt=cutoff_date
            )

            count = inactive_guests.count()
            inactive_guests.delete()

            logger.info(f"Cleaned up {count} inactive guest users")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up inactive guests: {e}")
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

    def get_users_with_statistics(self) -> QuerySet[CustomUser]:
        """Get users with event participation statistics"""
        return CustomUser.objects.select_related().annotate(
            events_owned=Count("created_events", distinct=True),
            events_participated=Count("joined_events", distinct=True),
        )
