"""
Service Factory for Dependency Injection

Provides centralized service creation and lifecycle management with proper 
dependency injection to reduce coupling between views and service implementations.
"""

import logging
from typing import Dict, Type, Optional, Any, Callable
from threading import RLock

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Registry for service types and their configurations.
    
    This registry maintains information about how to create services,
    their dependencies, and lifecycle management.
    """
    
    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = RLock()
    
    def register_service(
        self,
        service_name: str,
        service_class: Type,
        dependencies: Optional[Dict[str, str]] = None,
        singleton: bool = False,
        factory_func: Optional[Callable] = None
    ) -> None:
        """
        Register a service with the registry.
        
        Args:
            service_name: Unique name for the service
            service_class: Service class to instantiate
            dependencies: Map of constructor params to other service names
            singleton: Whether to maintain single instance
            factory_func: Custom factory function for complex initialization
        """
        with self._lock:
            self._services[service_name] = {
                'class': service_class,
                'dependencies': dependencies or {},
                'singleton': singleton,
                'factory_func': factory_func
            }
            
        logger.debug(f"Registered service: {service_name} ({service_class.__name__})")
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service configuration by name."""
        return self._services.get(service_name)
    
    def has_service(self, service_name: str) -> bool:
        """Check if service is registered."""
        return service_name in self._services
    
    def clear_instances(self) -> None:
        """Clear all singleton instances (useful for testing)."""
        with self._lock:
            self._instances.clear()
    
    def get_singleton_instance(self, service_name: str) -> Optional[Any]:
        """Get singleton instance if exists."""
        return self._instances.get(service_name)
    
    def set_singleton_instance(self, service_name: str, instance: Any) -> None:
        """Set singleton instance."""
        with self._lock:
            self._instances[service_name] = instance


class ServiceFactory:
    """
    Main service factory for creating and managing service instances.
    
    This factory handles dependency resolution, lifecycle management,
    and provides a clean interface for views to obtain services.
    """
    
    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self.registry = registry or ServiceRegistry()
        self._creation_stack = set()  # For circular dependency detection
    
    def create_service(self, service_name: str, **override_kwargs) -> Any:
        """
        Create service instance with dependency injection.
        
        Args:
            service_name: Name of service to create
            **override_kwargs: Override specific constructor arguments
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service not registered or circular dependency detected
        """
        if not self.registry.has_service(service_name):
            raise ValueError(f"Service not registered: {service_name}")
        
        # Check for circular dependencies
        if service_name in self._creation_stack:
            raise ValueError(f"Circular dependency detected for service: {service_name}")
        
        config = self.registry.get_service_config(service_name)
        
        # Check for singleton instance
        if config['singleton']:
            instance = self.registry.get_singleton_instance(service_name)
            if instance is not None:
                return instance
        
        try:
            self._creation_stack.add(service_name)
            instance = self._create_instance(service_name, config, override_kwargs)
            
            # Store singleton instance
            if config['singleton']:
                self.registry.set_singleton_instance(service_name, instance)
            
            return instance
            
        finally:
            self._creation_stack.discard(service_name)
    
    def _create_instance(self, service_name: str, config: Dict[str, Any], override_kwargs: Dict[str, Any]) -> Any:
        """Create service instance with proper dependency injection."""
        
        # Use custom factory function if provided
        if config['factory_func']:
            return config['factory_func'](self, **override_kwargs)
        
        # Resolve dependencies
        constructor_kwargs = {}
        
        for param_name, dependency_service in config['dependencies'].items():
            if param_name not in override_kwargs:
                try:
                    constructor_kwargs[param_name] = self.create_service(dependency_service)
                except ValueError as e:
                    logger.warning(f"Failed to resolve dependency {dependency_service} for {service_name}: {e}")
                    # Continue without this dependency (service should handle None gracefully)
                    constructor_kwargs[param_name] = None
        
        # Add any override kwargs
        constructor_kwargs.update(override_kwargs)
        
        # Create instance
        service_class = config['class']
        try:
            instance = service_class(**constructor_kwargs)
            logger.debug(f"Created service instance: {service_name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create service {service_name}: {e}")
            raise ValueError(f"Service creation failed for {service_name}: {e}")


# Global service registry and factory
_global_registry = ServiceRegistry()
_global_factory = ServiceFactory(_global_registry)


def register_service(
    service_name: str,
    service_class: Type,
    dependencies: Optional[Dict[str, str]] = None,
    singleton: bool = False,
    factory_func: Optional[Callable] = None
) -> None:
    """
    Register a service with the global registry.
    
    Args:
        service_name: Unique name for the service
        service_class: Service class to instantiate
        dependencies: Map of constructor params to other service names
        singleton: Whether to maintain single instance
        factory_func: Custom factory function
    """
    _global_registry.register_service(
        service_name=service_name,
        service_class=service_class,
        dependencies=dependencies,
        singleton=singleton,
        factory_func=factory_func
    )


def get_service(service_name: str, **kwargs) -> Any:
    """
    Get service instance from global factory.
    
    Args:
        service_name: Name of service to create
        **kwargs: Override constructor arguments
        
    Returns:
        Service instance
    """
    return _global_factory.create_service(service_name, **kwargs)


def clear_service_cache() -> None:
    """Clear all singleton instances (useful for testing)."""
    _global_registry.clear_instances()


# Service name constants to avoid magic strings
class ServiceNames:
    """Constants for service names to avoid magic strings."""
    EVENT_SERVICE = 'event_service'
    ALBUM_SERVICE = 'album_service'
    USER_SERVICE = 'user_service'
    MEDIAFILE_SERVICE = 'mediafile_service'
    PERMISSION_SERVICE = 'permission_service'
    S3_SERVICE = 's3_service'
    EVENT_DAL = 'event_dal'
    ALBUM_DAL = 'album_dal'
    USER_DAL = 'user_dal'


def register_default_services():
    """
    Register default services with their dependencies.
    
    This function should be called during application startup to register
    all the core services used throughout the application.
    """
    # Register DAL services (usually singletons for connection pooling)
    register_service(
        ServiceNames.EVENT_DAL,
        None,  # Will be set when DAL classes are imported
        singleton=True
    )
    
    register_service(
        ServiceNames.ALBUM_DAL,
        None,  # Will be set when DAL classes are imported
        singleton=True
    )
    
    # Register core services with their dependencies
    register_service(
        ServiceNames.USER_SERVICE,
        None,  # Will be set when service classes are imported
        dependencies={'dal': ServiceNames.USER_DAL},
        singleton=False  # User services might need different configurations
    )
    
    register_service(
        ServiceNames.PERMISSION_SERVICE,
        None,  # Will be set when EventPermissionService is imported
        dependencies={'dal': ServiceNames.EVENT_DAL},
        singleton=True  # Permission logic is stateless and cacheable
    )
    
    register_service(
        ServiceNames.EVENT_SERVICE,
        None,  # Will be set when service classes are imported
        dependencies={
            'dal': ServiceNames.EVENT_DAL,
            'permission_service': ServiceNames.PERMISSION_SERVICE,
            's3_service': ServiceNames.S3_SERVICE
        },
        singleton=False  # Event services might need different user contexts
    )
    
    register_service(
        ServiceNames.S3_SERVICE,
        None,  # Will be set when S3Service is imported
        singleton=True  # S3 service can be shared
    )
    
    register_service(
        ServiceNames.ALBUM_SERVICE,
        None,  # Will be set when service classes are imported
        dependencies={
            'permission_service': ServiceNames.PERMISSION_SERVICE,
            's3service': ServiceNames.S3_SERVICE
        },
        singleton=False
    )
    
    logger.info("Registered default services with dependency injection")


def update_service_class(service_name: str, service_class: Type) -> None:
    """
    Update the class for an already registered service.
    
    This is useful for updating service registrations after the classes
    are imported during Django startup.
    
    Args:
        service_name: Name of service to update
        service_class: New service class
    """
    config = _global_registry.get_service_config(service_name)
    if config:
        config['class'] = service_class
        logger.debug(f"Updated service class for {service_name}: {service_class.__name__}")
    else:
        logger.warning(f"Attempted to update non-existent service: {service_name}")