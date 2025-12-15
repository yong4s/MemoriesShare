"""
Shared Interfaces Module

Contains abstract interfaces for service decoupling and dependency injection.
These interfaces help break circular dependencies and enable better testing.
"""

# Only permission interface remains after enterprise interface cleanup
from .permission_interface import IPermissionValidator
from .permission_interface import SimplePermissionValidator

__all__ = [
    # Permission interfaces
    "IPermissionValidator",
    "SimplePermissionValidator",
]
