"""
Shared Interfaces Module

Contains abstract interfaces for service decoupling and dependency injection.
"""

from apps.shared.interfaces.permission_interface import IPermissionValidator

__all__ = [
    'IPermissionValidator',
]
