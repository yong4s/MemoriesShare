"""
User Data Access Layer (DAL)

Handles all database operations for the unified CustomUser model.
Provides optimized queries with proper select_related and prefetch_related usage.
"""

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
    """
    Data Access Layer for CustomUser operations.

    Encapsulates all database queries and optimizations for user management.
    Prevents N+1 queries through strategic use of select_related and prefetch_related.
    """

    # =============================================================================
    # BASIC CRUD OPERATIONS
    # =============================================================================

    def get_by_id(self, user_id: int) -> CustomUser | None:
        """
        Get user by ID with optimized query.

        Args:
            user_id: User ID to retrieve

        Returns:
            CustomUser instance or None
        """
        try:
            return CustomUser.objects.select_related().get(id=user_id)
        except CustomUser.DoesNotExist:
            return None

    def get_by_uuid(self, user_uuid: str) -> CustomUser | None:
        """
        Get user by UUID.

        Args:
            user_uuid: User UUID to retrieve

        Returns:
            CustomUser instance or None
        """
        try:
            return CustomUser.objects.select_related().get(user_uuid=user_uuid)
        except CustomUser.DoesNotExist:
            return None

    def get_by_email(self, email: str, registered_only: bool = True) -> CustomUser | None:
        """
        Get user by email with case-insensitive lookup.

        Args:
            email: Email address to search for
            registered_only: Only search registered users

        Returns:
            CustomUser instance or None
        """
        if not email:
            return None

        queryset = CustomUser.objects.select_related()

        if registered_only:
            queryset = queryset.filter(is_registered=True)

        try:
            return queryset.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return None

    def get_by_clerk_id(self, clerk_id: str) -> CustomUser | None:
        """
        Get user by Clerk authentication ID.

        Args:
            clerk_id: Clerk user identifier

        Returns:
            CustomUser instance or None
        """
        if not clerk_id:
            return None

        try:
            return CustomUser.objects.select_related().get(clerk_id=clerk_id, is_registered=True)
        except CustomUser.DoesNotExist:
            return None

    def get_by_invite_token(self, invite_token: str) -> CustomUser | None:
        """
        Get guest user by invitation token.

        Args:
            invite_token: Invitation token to search for

        Returns:
            CustomUser instance or None
        """
        if not invite_token:
            return None

        try:
            return CustomUser.objects.select_related().get(invite_token_used=invite_token, is_registered=False)
        except CustomUser.DoesNotExist:
            return None

    # =============================================================================
    # USER CREATION OPERATIONS
    # =============================================================================

    def create_registered_user(
        self, email: str, password: str, first_name: str = '', last_name: str = '', **extra_fields
    ) -> CustomUser:
        """
        Create a registered user through the manager.

        Args:
            email: User email
            password: User password
            first_name: Optional first name
            last_name: Optional last name
            **extra_fields: Additional fields

        Returns:
            Created CustomUser instance

        Raises:
            IntegrityError: If email already exists
            ValidationError: If validation fails
        """
        try:
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                is_registered=True,
                first_name=first_name,
                last_name=last_name,
                **extra_fields,
            )

            logger.info(f'Created registered user in DAL: {email} (ID: {user.id})')
            return user

        except IntegrityError as e:
            logger.error(f'Integrity error creating registered user: {e}')
            raise
        except ValidationError as e:
            logger.error(f'Validation error creating registered user: {e}')
            raise

    def create_guest_user(self, guest_name: str, invite_token: str = None, **extra_fields) -> CustomUser:
        """
        Create a guest user through the manager.

        Args:
            guest_name: Display name for guest
            invite_token: Optional invitation token
            **extra_fields: Additional fields

        Returns:
            Created CustomUser instance

        Raises:
            ValidationError: If validation fails
        """
        try:
            user = CustomUser.objects.create_guest_user(
                guest_name=guest_name, invite_token=invite_token, **extra_fields
            )

            logger.info(f'Created guest user in DAL: {guest_name} (ID: {user.id})')
            return user

        except ValidationError as e:
            logger.error(f'Validation error creating guest user: {e}')
            raise

    def update_user(self, user: CustomUser, **update_fields) -> CustomUser:
        """
        Update user with provided fields.

        Args:
            user: CustomUser instance to update
            **update_fields: Fields to update

        Returns:
            Updated CustomUser instance

        Raises:
            ValidationError: If validation fails
        """
        try:
            for field, value in update_fields.items():
                if hasattr(user, field):
                    setattr(user, field, value)

            user.full_clean()  # Validate before saving
            user.save()

            logger.info(f'Updated user {user.id} in DAL')
            return user

        except ValidationError as e:
            logger.error(f'Validation error updating user {user.id}: {e}')
            raise

    def delete_user(self, user: CustomUser) -> None:
        """
        Delete user from database.

        Args:
            user: CustomUser instance to delete
        """
        user_id = user.id
        user.delete()
        logger.info(f'Deleted user {user_id} from DAL')

    # =============================================================================
    # QUERY OPERATIONS WITH OPTIMIZATION
    # =============================================================================

    def get_registered_users(self, limit: int = None, active_only: bool = True) -> list[CustomUser]:
        """
        Get list of registered users with optimized query.

        Args:
            limit: Optional limit on number of users
            active_only: Only return active users

        Returns:
            List of CustomUser instances
        """
        queryset = CustomUser.objects.registered_users()

        if active_only:
            queryset = queryset.filter(is_active=True)

        queryset = queryset.order_by('email')

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    def get_guest_users(self, limit: int = None, active_only: bool = True) -> list[CustomUser]:
        """
        Get list of guest users with optimized query.

        Args:
            limit: Optional limit on number of users
            active_only: Only return active users

        Returns:
            List of CustomUser instances
        """
        queryset = CustomUser.objects.guest_users()

        if active_only:
            queryset = queryset.filter(is_active=True)

        queryset = queryset.order_by('-created_at')

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    def search_users(self, query: str, registered_only: bool = True, limit: int = 50) -> list[CustomUser]:
        """
        Search users by name or email.

        Args:
            query: Search query
            registered_only: Only search registered users
            limit: Maximum number of results

        Returns:
            List of matching CustomUser instances
        """
        if not query or len(query.strip()) < 2:
            return []

        query = query.strip()

        # Build search query
        search_q = Q()

        # Search in email for registered users
        if registered_only:
            search_q |= Q(email__icontains=query, is_registered=True)
            search_q |= Q(first_name__icontains=query, is_registered=True)
            search_q |= Q(last_name__icontains=query, is_registered=True)
        else:
            # Search in all relevant fields for all users
            search_q |= Q(email__icontains=query)
            search_q |= Q(first_name__icontains=query)
            search_q |= Q(last_name__icontains=query)
            search_q |= Q(guest_name__icontains=query, is_registered=False)

        queryset = CustomUser.objects.filter(search_q).filter(is_active=True)

        if registered_only:
            queryset = queryset.filter(is_registered=True)

        # Order by relevance (exact matches first)
        queryset = queryset.order_by('email', 'first_name', 'last_name')

        return list(queryset[:limit])

    def get_users_with_participations(self, user_ids: list[int] = None) -> QuerySet[CustomUser]:
        """
        Get users with their event participations prefetched.
        Optimized for displaying user event history.

        Args:
            user_ids: Optional list of specific user IDs

        Returns:
            QuerySet with prefetched participations
        """
        queryset = CustomUser.objects.select_related().prefetch_related('event_participations__event', 'joined_events')

        if user_ids:
            queryset = queryset.filter(id__in=user_ids)

        return queryset

    def get_users_by_event(self, event_id: int) -> QuerySet[CustomUser]:
        """
        Get all users participating in a specific event.

        Args:
            event_id: Event ID to filter by

        Returns:
            QuerySet of CustomUser instances participating in the event
        """
        return (
            CustomUser.objects.filter(event_participations__event_id=event_id)
            .select_related()
            .prefetch_related('event_participations')
            .distinct()
        )

    # =============================================================================
    # STATISTICS AND COUNTS
    # =============================================================================

    def get_user_count(self) -> int:
        """Get total user count"""
        return CustomUser.objects.count()

    def get_registered_user_count(self) -> int:
        """Get count of registered users"""
        return CustomUser.objects.filter(is_registered=True).count()

    def get_guest_user_count(self) -> int:
        """Get count of guest users"""
        return CustomUser.objects.filter(is_registered=False).count()

    def get_active_user_count(self) -> int:
        """Get count of active users"""
        return CustomUser.objects.filter(is_active=True).count()

    def get_inactive_user_count(self) -> int:
        """Get count of inactive users"""
        return CustomUser.objects.filter(is_active=False).count()

    def get_user_statistics_by_period(self, days: int = 30) -> dict[str, int]:
        """
        Get user registration statistics for a time period.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with statistics
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        return {
            'new_registered_users': CustomUser.objects.filter(is_registered=True, date_joined__gte=cutoff_date).count(),
            'new_guest_users': CustomUser.objects.filter(is_registered=False, created_at__gte=cutoff_date).count(),
            'total_new_users': CustomUser.objects.filter(created_at__gte=cutoff_date).count(),
        }

    # =============================================================================
    # MAINTENANCE OPERATIONS
    # =============================================================================

    def cleanup_inactive_guests(self, days_old: int = 30) -> int:
        """
        Delete old inactive guest users.

        Args:
            days_old: Delete guests older than this many days

        Returns:
            Number of users deleted
        """
        cutoff_date = timezone.now() - timedelta(days=days_old)

        old_guests = CustomUser.objects.filter(is_registered=False, is_active=False, created_at__lt=cutoff_date)

        count = old_guests.count()
        old_guests.delete()

        logger.info(f'Cleaned up {count} inactive guest users older than {days_old} days')
        return count

    def find_duplicate_emails(self) -> list[dict[str, Any]]:
        """
        Find users with duplicate email addresses.

        Returns:
            List of dictionaries with duplicate email information
        """
        duplicates = (
            CustomUser.objects.values('email').annotate(count=Count('email')).filter(count__gt=1, email__isnull=False)
        )

        result = []
        for duplicate in duplicates:
            email = duplicate['email']
            users = CustomUser.objects.filter(email=email).values(
                'id', 'email', 'is_registered', 'is_active', 'created_at'
            )
            result.append({'email': email, 'count': duplicate['count'], 'users': list(users)})

        return result

    def get_users_without_participations(self) -> QuerySet[CustomUser]:
        """
        Get users who have never participated in any events.

        Returns:
            QuerySet of CustomUser instances with no event participations
        """
        return CustomUser.objects.filter(event_participations__isnull=True).select_related()

    # =============================================================================
    # BULK OPERATIONS
    # =============================================================================

    def bulk_update_users(self, user_ids: list[int], update_fields: dict[str, Any]) -> int:
        """
        Bulk update multiple users.

        Args:
            user_ids: List of user IDs to update
            update_fields: Fields to update

        Returns:
            Number of users updated
        """
        users = CustomUser.objects.filter(id__in=user_ids)
        count = users.update(**update_fields)

        logger.info(f'Bulk updated {count} users in DAL')
        return count

    def bulk_deactivate_users(self, user_ids: list[int]) -> int:
        """
        Bulk deactivate multiple users.

        Args:
            user_ids: List of user IDs to deactivate

        Returns:
            Number of users deactivated
        """
        return self.bulk_update_users(user_ids, {'is_active': False})

    def bulk_activate_users(self, user_ids: list[int]) -> int:
        """
        Bulk activate multiple users.

        Args:
            user_ids: List of user IDs to activate

        Returns:
            Number of users activated
        """
        return self.bulk_update_users(user_ids, {'is_active': True})
