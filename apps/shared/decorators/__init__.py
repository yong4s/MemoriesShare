"""
Shared decorators for Media Flow application.

This module provides reusable decorators for common concerns:
- Database error handling
- Caching
- Logging
- Performance monitoring
"""

from apps.shared.decorators.database import handle_db_errors

__all__ = [
    'handle_db_errors',
]
