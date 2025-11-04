"""
Shared Authentication Permissions

This module contains permission classes for JWT-based authentication
and other shared permission logic.
"""

from rest_framework.permissions import BasePermission
from rest_framework_api_key.permissions import HasAPIKey


class HasJWTAuth(BasePermission):
    """
    Permission that checks for valid JWT authentication or API key.

    This is a placeholder permission class that allows authenticated users
    with either JWT tokens or API keys to access the resource.
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to access the resource.

        Returns True if:
        - User is authenticated (JWT token)
        - Or has valid API key
        """
        # Check for JWT authentication
        if request.user and request.user.is_authenticated:
            return True

        # Check for API key authentication
        api_key_permission = HasAPIKey()
        if api_key_permission.has_permission(request, view):
            return True

        return False
