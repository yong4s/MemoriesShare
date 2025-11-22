"""
Core Business Exception Hierarchy for Media Flow

Following Enterprise Error Handling patterns:
- Clean separation between business and HTTP layers
- Exception Translation from DAL → Service → View layers
- Type-safe error handling with semantic meaning

These exceptions represent BUSINESS failures, not HTTP responses.
HTTP mapping happens in the API exception handler.
"""

import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """
    Base class for all business logic errors in the application.
    
    This is NOT an HTTP exception - it's a pure business domain error.
    HTTP status codes are mapped by the API exception handler.
    """
    
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        
    def __str__(self) -> str:
        return self.message
        
    def get_context(self) -> dict:
        """Get additional error context for logging/debugging"""
        return self.context


class ResourceNotFoundError(AppError):
    """
    Raised when a requested resource doesn't exist.
    
    Examples:
    - Event not found by UUID
    - User not found by ID
    - File not found in S3
    
    HTTP Mapping: 404 NOT FOUND
    """
    pass


class BusinessRuleViolation(AppError):
    """
    Raised when user action violates business logic rules.
    
    Examples:
    - Trying to invite guests to past events
    - Non-owner trying to delete event
    - Exceeding capacity limits
    - Invalid state transitions
    
    HTTP Mapping: 409 CONFLICT or 400 BAD REQUEST
    """
    pass


class ValidationError(AppError):
    """
    Raised when input data fails business validation.
    
    Examples:
    - Invalid email format in service layer
    - Business constraint violations
    - Data integrity issues
    
    HTTP Mapping: 400 BAD REQUEST
    """
    
    def __init__(self, message: str, field_errors: dict = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field_errors = field_errors or {}


class PermissionError(AppError):
    """
    Raised when user lacks required permissions for business operation.
    
    Examples:
    - Guest trying to delete event
    - User accessing private event
    - Insufficient role for action
    
    HTTP Mapping: 403 FORBIDDEN
    """
    pass


class ServiceUnavailableError(AppError):
    """
    Raised when external service dependencies fail.
    
    Examples:
    - S3 upload failures
    - Database connection issues
    - External API timeouts
    - Cache service failures
    
    HTTP Mapping: 503 SERVICE UNAVAILABLE
    """
    pass


class AuthenticationError(AppError):
    """
    Raised when user authentication fails at business layer.
    
    Examples:
    - Invalid JWT tokens (business validation)
    - Expired credentials
    - User account disabled
    
    HTTP Mapping: 401 UNAUTHORIZED
    """
    pass


class ConfigurationError(AppError):
    """
    Raised when application configuration is invalid.
    
    Examples:
    - Missing required settings
    - Invalid service configurations
    - Misconfigured external services
    
    HTTP Mapping: 500 INTERNAL SERVER ERROR
    """
    pass


# Convenience functions for common patterns
def resource_not_found(resource_type: str, identifier: str, **context) -> ResourceNotFoundError:
    """Factory function for consistent resource not found errors"""
    message = f"{resource_type} with identifier '{identifier}' not found"
    error_code = f"{resource_type.lower()}_not_found"
    return ResourceNotFoundError(
        message=message, 
        error_code=error_code, 
        context={'resource_type': resource_type, 'identifier': identifier, **context}
    )


def permission_denied(action: str, resource: str, user_id: int = None, **context) -> PermissionError:
    """Factory function for consistent permission errors"""
    message = f"Permission denied for action '{action}' on {resource}"
    error_code = f"{action}_permission_denied"
    return PermissionError(
        message=message,
        error_code=error_code,
        context={'action': action, 'resource': resource, 'user_id': user_id, **context}
    )


def business_rule_violated(rule_name: str, details: str, **context) -> BusinessRuleViolation:
    """Factory function for business rule violations"""
    message = f"Business rule violation: {rule_name}. {details}"
    error_code = f"{rule_name.lower()}_violation"
    return BusinessRuleViolation(
        message=message,
        error_code=error_code,
        context={'rule_name': rule_name, 'details': details, **context}
    )