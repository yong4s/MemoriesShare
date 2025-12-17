from rest_framework.permissions import BasePermission

from apps.accounts.models.custom_user import CustomUser


class IsUserOwner(BasePermission):
    """Permission to check if user can access/modify their own data"""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if isinstance(obj, CustomUser):
            return obj.id == request.user.id

        # If obj has user attribute (profile, session, etc.)
        user = getattr(obj, 'user', None)
        if user:
            return user.id == request.user.id

        return False


class IsRegisteredUser(BasePermission):
    """Permission to check if user is registered (not guest)"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'is_registered') and request.user.is_registered


class IsGuestUser(BasePermission):
    """Permission to check if user is guest"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'is_guest') and request.user.is_guest


class CanAccessUserData(BasePermission):
    """Permission to check if user can access user data (own data or admin)"""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Admin can access any user data
        if request.user.is_staff or request.user.is_superuser:
            return True

        # User can access own data
        if isinstance(obj, CustomUser):
            return obj.id == request.user.id

        # If obj has user attribute
        user = getattr(obj, 'user', None)
        if user:
            return user.id == request.user.id

        return False


class CanModifyUserAccount(BasePermission):
    """Permission to check if user can modify account settings"""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Only the user themselves can modify their account
        if isinstance(obj, CustomUser):
            return obj.id == request.user.id

        return False


class IsActiveUser(BasePermission):
    """Permission to check if user account is active"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active


class AccountPermissionMixin:
    """Mixin to provide user object for permission checks"""

    def get_object(self):
        """Get user object based on URL parameter or current user"""
        user_id = self.kwargs.get('user_id')

        if user_id:
            try:
                return CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return None

        # Default to current user for profile operations
        return self.request.user if self.request.user.is_authenticated else None
