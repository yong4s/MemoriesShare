"""
Shared Interfaces Module

Contains abstract interfaces for service decoupling and dependency injection.
These interfaces help break circular dependencies and enable better testing.
"""

from .permission_interface import IPermissionValidator, SimplePermissionValidator
from .service_interfaces import (
    IEventService,
    IAlbumService,
    IUserService,
    IS3Service,
    IDataAccessLayer,
    IEventDAL,
    IAlbumDAL,
)

__all__ = [
    # Permission interfaces
    'IPermissionValidator',
    'SimplePermissionValidator',
    
    # Service interfaces
    'IEventService',
    'IAlbumService',
    'IUserService',
    'IS3Service',
    
    # DAL interfaces
    'IDataAccessLayer',
    'IEventDAL',
    'IAlbumDAL',
]