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


class CanModifyUserAccount(BasePermission):
    """Permission to check if user can modify account settings"""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Only the user themselves can modify their account
        if isinstance(obj, CustomUser):
            return obj.id == request.user.id

        return False
