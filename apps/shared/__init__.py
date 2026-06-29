"""
Shared utilities and base models for the Media Flow application

This module provides organized access to all shared functionality:
- Base models (BaseModel for timestamps)
- Authentication (JWT via django-rest-framework-simplejwt, permissions)
- Storage (S3Service and backends)
- Exceptions (custom exceptions)
- Utilities (validators, helpers)

Import specific classes directly from their submodules:
- from apps.shared.base.models import BaseModel
- etc.
"""

# Empty init to avoid circular imports
# All imports should be done directly from submodules
