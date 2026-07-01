from collections.abc import Callable
from typing import Any
from typing import Optional
from typing import Type

from apps.accounts.cache.user_cache_service import user_cache_service
from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.user_service import UserService
from apps.albums.cache.album_cache_service import album_cache_service
from apps.albums.dal.album_dal import AlbumDAL
from apps.albums.services.album_service import AlbumService
from apps.events.cache.event_cache_invalidator import EventCacheInvalidator
from apps.events.cache.event_cache_service import event_cache_service
from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.dal.invite_link_event_dal import InviteLinkEventDAL
from apps.events.services.event_analytics_service import event_analytics_service
from apps.events.services.event_service import EventService
from apps.events.services.invite_link_service import InviteLinkService
from apps.events.services.permission_service import EventPermissionService
from apps.mediafiles.dal.media_file_dal import MediaFileDAL
from apps.mediafiles.services.media_file_s3_service import MediaFileS3Service
from apps.mediafiles.services.media_file_service import MediaFileService
from apps.shared.storage.optimized_s3_service import get_optimized_s3_service


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
        self._dal_factories = {
            'user_dal': UserDAL,
            'event_dal': EventDAL,
            'participant_dal': EventParticipantDAL,
            'analytics_dal': EventAnalyticsDAL,
            'invite_link_dal': InviteLinkEventDAL,
            'media_file_dal': MediaFileDAL,
            'album_dal': AlbumDAL,
        }

        self._service_factories = {
            'user_service': UserService,
            'auth_service': AuthService,
            # s3_service is a process-wide singleton; the factory returns the
            # same instance on every call (one boto3 client per worker).
            's3_service': get_optimized_s3_service,
            'permission_service': EventPermissionService,
        }

    def event_service(self):
        """Create EventService with all dependencies injected.

        S3 cleanup moved to apps.events.tasks (Celery), so EventService no
        longer needs s3_service injection.
        """
        return EventService(
            dal=self._dal_factories['event_dal'](),
            participant_dal=self._dal_factories['participant_dal'](),
            permission_service=self._service_factories['permission_service'](),
            cache_service=event_cache_service,
            cache_invalidator=self.cache_invalidator(),
        )

    def user_service(self):
        """Create UserService with dependencies"""
        return self._service_factories['user_service'](dal=self._dal_factories['user_dal']())

    def auth_service(self):
        """Create AuthService with dependencies"""
        return self._service_factories['auth_service'](user_dal=self._dal_factories['user_dal']())

    def mediafile_service(self):
        """Create MediaFileService with dependencies"""
        return MediaFileService(
            dal=self._dal_factories['media_file_dal'](),
            s3_service=MediaFileS3Service(
                s3_service=self._service_factories['s3_service'](),
            ),
            permission_service=self._service_factories['permission_service'](),
        )

    def album_service(self):
        """Create AlbumService with all dependencies injected"""
        return AlbumService(
            dal=self._dal_factories['album_dal'](),
            permission_service=self._service_factories['permission_service'](),
            cache_service=album_cache_service,
        )

    def permission_service(self):
        """Create EventPermissionService with dependencies"""
        return self._service_factories['permission_service']()

    def cache_invalidator(self):
        """Create EventCacheInvalidator (cheap stateless collaborator)."""
        return EventCacheInvalidator(event_cache=event_cache_service, user_cache=user_cache_service)

    def invite_link_service(self):
        """Create InviteLinkService with dependencies"""
        return InviteLinkService(
            dal=self._dal_factories['invite_link_dal'](),
            event_dal=self._dal_factories['event_dal'](),
            participant_dal=self._dal_factories['participant_dal'](),
            user_dal=self._dal_factories['user_dal'](),
            permission_service=self.permission_service(),
            cache_invalidator=self.cache_invalidator(),
        )

    def analytics_service(self):  # noqa: PLR6301
        """Return the EventAnalyticsService module-level singleton.

        Intentionally an instance method (consistent with other factories)
        even though no `self` is needed — analytics is a process-wide cache
        holder; tests that need a replacement should patch
        `apps.events.services.event_analytics_service.event_analytics_service`
        directly.
        """
        return event_analytics_service

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


def get_user_service():
    """Quick access to UserService"""
    return get_container().user_service()


def get_auth_service():
    """Quick access to AuthService"""
    return get_container().auth_service()


def get_album_service():
    """Quick access to AlbumService"""
    return get_container().album_service()


def get_mediafile_service():
    """Quick access to MediafileService"""
    return get_container().mediafile_service()


def get_permission_service():
    """Quick access to EventPermissionService"""
    return get_container().permission_service()


def get_invite_link_service():
    """Quick access to InviteLinkService"""
    return get_container().invite_link_service()


def get_analytics_service():
    """Quick access to EventAnalyticsService (module singleton)"""
    return get_container().analytics_service()


def get_s3_service():
    """Quick access to OptimizedS3Service"""
    return get_container()._service_factories['s3_service']()


def get_analytics_dal():
    """Quick access to EventAnalyticsDAL"""
    return get_container()._dal_factories['analytics_dal']()
