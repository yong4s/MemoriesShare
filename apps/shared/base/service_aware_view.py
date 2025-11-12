"""
Service-Aware Base Views

Provides base view classes that use dependency injection through the service factory,
reducing coupling and enabling better testing and configuration management.
"""

import logging
from typing import Any, Optional

from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.shared.interfaces.service_interfaces import IEventService, IAlbumService, IUserService, IS3Service
from apps.shared.interfaces.permission_interface import IPermissionValidator
from apps.shared.services.service_factory import get_service, ServiceNames

logger = logging.getLogger(__name__)


class ServiceAwareAPIView(APIView):
    """
    Enhanced base API view with service factory integration.
    
    This view provides access to services through dependency injection,
    eliminating the need for direct service instantiation and enabling
    better testing and configuration management.
    """
    
    authentication_classes = (JWTAuthentication,)
    
    # Service cache for request lifecycle
    _service_cache = None
    
    def setup(self, request, *args, **kwargs):
        """Initialize view with fresh service cache per request."""
        super().setup(request, *args, **kwargs)
        self._service_cache = {}
    
    def get_service(self, service_name: str, **kwargs) -> Any:
        """
        Get service instance with caching for request lifecycle.
        
        Args:
            service_name: Name of service (use ServiceNames constants)
            **kwargs: Override constructor arguments
            
        Returns:
            Service instance
        """
        # Create cache key including kwargs for uniqueness
        cache_key = f"{service_name}_{hash(frozenset(kwargs.items()))}"
        
        if cache_key not in self._service_cache:
            try:
                self._service_cache[cache_key] = get_service(service_name, **kwargs)
                logger.debug(f"Created service instance: {service_name} for view: {self.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to create service {service_name} in view {self.__class__.__name__}: {e}")
                raise
        
        return self._service_cache[cache_key]
    
    def get_event_service(self) -> IEventService:
        """Get EventService instance implementing IEventService interface."""
        return self.get_service(ServiceNames.EVENT_SERVICE)
    
    def get_user_service(self) -> IUserService:
        """Get UserService instance implementing IUserService interface."""
        return self.get_service(ServiceNames.USER_SERVICE)
    
    def get_album_service(self) -> IAlbumService:
        """Get AlbumService instance implementing IAlbumService interface."""
        return self.get_service(ServiceNames.ALBUM_SERVICE)
    
    def get_mediafile_service(self):
        """Get MediaFileService instance.""" 
        return self.get_service(ServiceNames.MEDIAFILE_SERVICE)
    
    def get_s3_service(self) -> IS3Service:
        """Get S3Service instance implementing IS3Service interface."""
        return self.get_service(ServiceNames.S3_SERVICE)
    
    def get_permission_service(self) -> IPermissionValidator:
        """Get permission validation service implementing IPermissionValidator interface."""
        return self.get_service(ServiceNames.PERMISSION_SERVICE)


class EventServiceMixin:
    """
    Mixin providing convenient access to event-related services.
    
    This mixin can be added to views that primarily work with events
    to provide convenient service access methods.
    """
    
    def get_event_service_with_user_context(self) -> IEventService:
        """Get EventService configured for current user context."""
        if not hasattr(self, 'request') or not self.request.user:
            return self.get_event_service()
        
        # Could add user-specific configuration here
        return self.get_event_service()


class AlbumServiceMixin:
    """
    Mixin providing convenient access to album-related services.
    
    This mixin can be added to views that primarily work with albums.
    """
    
    def get_album_service_with_permissions(self) -> IAlbumService:
        """Get AlbumService with proper permission validation."""
        permission_service = self.get_permission_service()
        return self.get_service(ServiceNames.ALBUM_SERVICE, permission_service=permission_service)


class CacheableServiceMixin:
    """
    Mixin for views that want to cache services across multiple requests.
    
    Note: Use with caution - only for stateless services and when you're sure
    about the lifecycle implications.
    """
    
    _class_service_cache = {}
    
    def get_cached_service(self, service_name: str, **kwargs) -> Any:
        """
        Get service with class-level caching.
        
        WARNING: Only use this for truly stateless services.
        """
        cache_key = f"{self.__class__.__name__}_{service_name}_{hash(frozenset(kwargs.items()))}"
        
        if cache_key not in self._class_service_cache:
            self._class_service_cache[cache_key] = get_service(service_name, **kwargs)
            logger.debug(f"Cached service at class level: {service_name}")
        
        return self._class_service_cache[cache_key]
    
    @classmethod
    def clear_service_cache(cls):
        """Clear class-level service cache."""
        cls._class_service_cache.clear()


# Backwards compatibility base class
class BaseAPIView(ServiceAwareAPIView):
    """
    Legacy base class for backwards compatibility.
    
    This provides the same interface as the old BaseAPIView but now
    uses the service factory pattern internally.
    """
    
    def get_service(self):
        """
        Legacy method - subclasses should override to specify service type.
        
        Returns:
            Service instance
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError('Subclasses must implement get_service() or use specific service methods')


# Factory function for creating view mixins
def create_service_mixin(*service_names):
    """
    Factory function to create custom service mixins.
    
    Args:
        *service_names: Names of services to provide convenient access for
        
    Returns:
        Mixin class with methods for each service
    """
    
    class CustomServiceMixin:
        """Dynamically generated service mixin."""
        pass
    
    for service_name in service_names:
        method_name = f"get_{service_name.replace('_service', '')}_service"
        
        def make_service_getter(svc_name):
            def getter(self):
                return self.get_service(svc_name)
            return getter
        
        setattr(CustomServiceMixin, method_name, make_service_getter(service_name))
    
    return CustomServiceMixin
