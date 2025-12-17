"""
Shared exceptions for Media Flow application.

This module provides:
1. Core business exceptions (core_exceptions.py)
2. Infrastructure exceptions (exception.py)
3. User-specific exceptions (user_exceptions.py)

Import business exceptions from core_exceptions for clean architecture.
"""

from apps.shared.exceptions.core_exceptions import AppError
from apps.shared.exceptions.core_exceptions import AuthenticationError
from apps.shared.exceptions.core_exceptions import business_rule_violated
from apps.shared.exceptions.core_exceptions import BusinessRuleViolation
from apps.shared.exceptions.core_exceptions import ConfigurationError
from apps.shared.exceptions.core_exceptions import permission_denied
from apps.shared.exceptions.core_exceptions import PermissionError
from apps.shared.exceptions.core_exceptions import resource_not_found
from apps.shared.exceptions.core_exceptions import ResourceNotFoundError
from apps.shared.exceptions.core_exceptions import ServiceUnavailableError
from apps.shared.exceptions.core_exceptions import ValidationError
from apps.shared.exceptions.exception import S3BucketNotFoundError
from apps.shared.exceptions.exception import S3BucketPermissionError
from apps.shared.exceptions.exception import S3ServiceError

# Re-export infrastructure exceptions for backward compatibility
from apps.shared.exceptions.exception import S3UploadException
from apps.shared.exceptions.exception import UserNotFoundError

__all__ = [
    # Core business exceptions
    'AppError',
    'AuthenticationError',
    'BusinessRuleViolation',
    'ConfigurationError',
    'PermissionError',
    'ResourceNotFoundError',
    'S3BucketNotFoundError',
    'S3BucketPermissionError',
    'S3ServiceError',
    # Infrastructure exceptions
    'S3UploadException',
    'ServiceUnavailableError',
    'UserNotFoundError',
    'ValidationError',
    'business_rule_violated',
    'permission_denied',
    # Factory functions
    'resource_not_found',
]
