"""
User-related Exception Classes

Custom exceptions for the unified user management system.
These exceptions provide clear error messages and proper HTTP status codes.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class UserException(APIException):
    """Base exception for all user-related errors"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A user error occurred'
    default_code = 'user_error'


class UserCreationError(UserException):
    """Raised when user creation fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'User creation failed'
    default_code = 'user_creation_error'


class UserValidationError(UserException):
    """Raised when user data validation fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'User data validation failed'
    default_code = 'user_validation_error'


class UserAuthenticationError(UserException):
    """Raised when user authentication fails"""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication failed'
    default_code = 'authentication_error'


class EmailAlreadyExistsError(UserException):
    """Raised when email address is already in use"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Email address is already in use'
    default_code = 'email_already_exists'


class GuestInviteRegisteredConflictError(UserException):
    """Raised when a guest invitation targets an email that belongs to a registered user.

    A registered account must explicitly accept an event invitation; silently
    linking it as a "guest" would be an authorization-bypass vector.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Email belongs to a registered account; explicit acceptance required'
    default_code = 'guest_invite_registered_conflict'

    def __init__(self, detail: str | None = None, code: str | None = None):
        super().__init__(detail=detail, code=code)
        self.error_code = code or self.default_code
