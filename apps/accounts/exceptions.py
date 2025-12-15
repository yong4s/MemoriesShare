"""
Domain-specific exceptions for Accounts app.

Following Clean Architecture principles, these exceptions are tightly coupled
to the accounts/user business domain and reside within the accounts app for high cohesion.
"""

from rest_framework.exceptions import APIException


class InvalidUserUUIdError(APIException):
    """Exception raised when user UUID format is invalid."""

    status_code = 400
    default_detail = "Invalid user UUID. Please provide a valid user UUID."
    default_code = "invalid_user_uuid"


class InvalidUserIdError(APIException):
    """Exception raised when user ID is invalid or user not found."""

    status_code = 400
    default_detail = "Invalid user ID. User not found."
    default_code = "invalid_user_id"


class GuestNotFoundError(APIException):
    """Exception raised when requested guest does not exist."""

    status_code = 404
    default_detail = "Guest not found."
    default_code = "guest_not_found"


class DuplicateGuestError(APIException):
    """Exception raised when guest with same email already exists for event."""

    status_code = 400
    default_detail = "Guest with this email already exists for this event."
    default_code = "duplicate_guest"


class InvalidGuestDataError(APIException):
    """Exception raised when guest data validation fails."""

    status_code = 400
    default_detail = "Invalid guest data provided."
    default_code = "invalid_guest_data"


class GuestPermissionError(APIException):
    """Exception raised when user lacks permission to access/modify guest."""

    status_code = 403
    default_detail = "Permission denied for guest operations."
    default_code = "guest_permission_denied"


class InvalidRSVPStatusError(APIException):
    """Exception raised when RSVP status is invalid."""

    status_code = 400
    default_detail = "Invalid RSVP status provided."
    default_code = "invalid_rsvp_status"


class GuestCapacityExceededError(APIException):
    """Exception raised when guest capacity for event is exceeded."""

    status_code = 400
    default_detail = "Cannot add more guests. Event capacity exceeded."
    default_code = "guest_capacity_exceeded"


class UserRegistrationError(APIException):
    """Exception raised when user registration fails."""

    status_code = 400
    default_detail = "User registration failed."
    default_code = "user_registration_error"


class UserAuthenticationError(APIException):
    """Exception raised when user authentication fails."""

    status_code = 401
    default_detail = "Authentication failed."
    default_code = "authentication_failed"


class UserProfileError(APIException):
    """Exception raised when user profile operations fail."""

    status_code = 400
    default_detail = "User profile operation failed."
    default_code = "user_profile_error"


class InvitationError(APIException):
    """Exception raised when invitation operations fail."""

    status_code = 400
    default_detail = "Invitation operation failed."
    default_code = "invitation_error"


class InvitationExpiredError(APIException):
    """Exception raised when invitation has expired."""

    status_code = 410
    default_detail = "Invitation has expired."
    default_code = "invitation_expired"
