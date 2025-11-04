"""
Shared utilities and base classes for the Media Flow application

This module provides organized access to all shared functionality:
- Base classes (BaseModel, BaseAPIView)
- Authentication (JWT, permissions)
- Storage (S3Service and backends)
- Exceptions (custom exceptions)
- Utilities (validators, helpers)

Import specific classes directly from their new locations:
- from apps.shared.base.base_api_view import BaseAPIView
- from apps.shared.auth.permissions import HasJWTAuth
- etc.
"""

# Empty init to avoid circular imports
# All imports should be done directly from submodules
