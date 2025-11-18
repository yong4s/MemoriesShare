
from typing import Type, Callable, Any, Optional
from apps.accounts.services.user_service import UserService
from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.services.event_service import EventService
from apps.events.services.permission_service import EventPermissionService
from apps.mediafiles.services.mediafile_service import MediafileService
from apps.shared.cache.cache_manager import CacheManager
from apps.shared.storage.optimized_s3_service import OptimizedS3Service


class Container:
    """
    Simple DI Container for managing service dependencies.
    
    Allows easy service creation and dependency injection without
    the complexity of enterprise factory patterns.
    """
    
    def __init__(self):
        # Service factory functions - can be overridden for testing
        self._dal_factories = {}
        self._service_factories = {}
        
        # Initialize default factories
        self._setup_default_factories()
    
    def _setup_default_factories(self):
        """Set up default factory functions for services"""
        # Register factory classes directly (no nested imports needed)
        self._dal_factories = {
            'event_dal': EventDAL,
            'participant_dal': EventParticipantDAL,
            'analytics_dal': EventAnalyticsDAL,
        }
        
        self._service_factories = {
            'user_service': UserService,
            's3_service': OptimizedS3Service,
            'cache_manager': CacheManager,
            'permission_service': EventPermissionService,
        }
    
    def event_service(self):
        """Create EventService with all dependencies injected"""
        return EventService(
            dal=self._dal_factories['event_dal'](),
            participant_dal=self._dal_factories['participant_dal'](),
            analytics_dal=self._dal_factories['analytics_dal'](),
            user_service=self._service_factories['user_service'](),
            s3_service=self._service_factories['s3_service'](),
            cache_manager=self._service_factories['cache_manager'](),
            permission_service=self._service_factories['permission_service'](),
        )
    
    def mediafile_service(self):
        """Create MediafileService with dependencies"""
        return MediafileService(
            s3service=self._service_factories['s3_service'](),
            permission_service=self._service_factories['permission_service'](),
        )
    
    def permission_service(self):
        """Create EventPermissionService with dependencies"""
        return self._service_factories['permission_service'](
            dal=self._dal_factories['event_dal'](),
            participant_dal=self._dal_factories['participant_dal'](),
            user_service=self._service_factories['user_service']()
        )
    
    # Override methods for testing
    def override_event_dal(self, factory: Callable):
        """Override EventDAL factory for testing"""
        self._dal_factories['event_dal'] = factory
    
    def override_s3_service(self, factory: Callable):
        """Override S3Service factory for testing"""
        self._service_factories['s3_service'] = factory
    
    def override_permission_service(self, factory: Callable):
        """Override PermissionService factory for testing"""
        self._service_factories['permission_service'] = factory
    
    def reset_to_defaults(self):
        """Reset all factories to defaults - useful for test cleanup"""
        self._setup_default_factories()


# Global container instance
_container = Container()


def get_container() -> Container:
    """Get the global container instance"""
    return _container


# Convenient functions for quick service access
def get_event_service():
    """Quick access to EventService"""
    return get_container().event_service()


def get_mediafile_service():
    """Quick access to MediafileService"""
    return get_container().mediafile_service()


def get_permission_service():
    """Quick access to EventPermissionService"""
    return get_container().permission_service()
