"""
Shared Services Module

Contains service layer utilities and factories for cross-app functionality.
"""

from .permission_factory import (
    PermissionServiceFactory,
    permission_factory,
    get_permission_validator,
    register_permission_service,
)

from .service_factory import (
    ServiceRegistry,
    ServiceFactory,
    ServiceNames,
    register_service,
    get_service,
    clear_service_cache,
    register_default_services,
    update_service_class,
)

__all__ = [
    # Permission factory
    'PermissionServiceFactory',
    'permission_factory',
    'get_permission_validator', 
    'register_permission_service',
    
    # Service factory
    'ServiceRegistry',
    'ServiceFactory', 
    'ServiceNames',
    'register_service',
    'get_service',
    'clear_service_cache',
    'register_default_services',
    'update_service_class',
]