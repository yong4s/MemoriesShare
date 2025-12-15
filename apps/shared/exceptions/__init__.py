"""
Shared exceptions for Media Flow application.

This module provides:
1. Core business exceptions (core_exceptions.py)
2. Infrastructure exceptions (exception.py)
3. User-specific exceptions (user_exceptions.py)

Import business exceptions from core_exceptions for clean architecture.
"""

from .core_exceptions import AppError
from .core_exceptions import AuthenticationError
from .core_exceptions import business_rule_violated
from .core_exceptions import BusinessRuleViolation
from .core_exceptions import ConfigurationError
from .core_exceptions import permission_denied
from .core_exceptions import PermissionError
from .core_exceptions import resource_not_found
from .core_exceptions import ResourceNotFoundError
from .core_exceptions import ServiceUnavailableError
from .core_exceptions import ValidationError
from .exception import S3BucketNotFoundError
from .exception import S3BucketPermissionError
from .exception import S3ServiceError

# Re-export infrastructure exceptions for backward compatibility
from .exception import S3UploadException
from .exception import UserNotFoundError

__all__ = [
    # Core business exceptions
    "AppError",
    "ResourceNotFoundError",
    "BusinessRuleViolation",
    "ValidationError",
    "PermissionError",
    "ServiceUnavailableError",
    "AuthenticationError",
    "ConfigurationError",
    # Factory functions
    "resource_not_found",
    "permission_denied",
    "business_rule_violated",
    # Infrastructure exceptions
    "S3UploadException",
    "S3ServiceError",
    "S3BucketNotFoundError",
    "S3BucketPermissionError",
    "UserNotFoundError",
]
