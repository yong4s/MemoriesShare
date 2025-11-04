"""
Custom authentication classes for API endpoints
"""

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Custom SessionAuthentication that doesn't enforce CSRF for API endpoints.

    This allows session-based authentication without requiring CSRF tokens,
    which is useful for API endpoints that need to support both session
    and token-based authentication.
    """

    def enforce_csrf(self, request):
        """
        Override to disable CSRF checking for API endpoints.
        """
        return  # Skip CSRF check for API endpoints
