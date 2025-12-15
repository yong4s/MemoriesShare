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
    default_detail = "A user error occurred"
    default_code = "user_error"


class UserCreationError(UserException):
    """Raised when user creation fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "User creation failed"
    default_code = "user_creation_error"


class UserValidationError(UserException):
    """Raised when user data validation fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "User data validation failed"
    default_code = "user_validation_error"


class UserAuthenticationError(UserException):
    """Raised when user authentication fails"""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed"
    default_code = "authentication_error"


class UserNotFoundError(UserException):
    """Raised when requested user is not found"""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "User not found"
    default_code = "user_not_found"


class EmailAlreadyExistsError(UserException):
    """Raised when email address is already in use"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Email address is already in use"
    default_code = "email_already_exists"


class UserPermissionError(UserException):
    """Raised when user lacks required permissions"""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Insufficient permissions"
    default_code = "permission_error"


class InvitationTokenError(UserException):
    """Raised when invitation token is invalid or expired"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid or expired invitation token"
    default_code = "invalid_invitation_token"


class UserConversionError(UserException):
    """Raised when converting between user types fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "User type conversion failed"
    default_code = "user_conversion_error"


class UserDeactivationError(UserException):
    """Raised when user deactivation fails"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "User deactivation failed"
    default_code = "user_deactivation_error"
