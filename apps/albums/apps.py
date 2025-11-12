from django.apps import AppConfig


class AlbumsConfig(AppConfig):
    """Configuration for the Albums application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.albums'
    verbose_name = 'Albums Management'

    def ready(self):
        """
        Application ready hook.
        
        Register album-related services with the service factory.
        """
        self._register_services()
    
    def _register_services(self):
        """Register all album-related services with the service factory."""
        from apps.shared.services.service_factory import update_service_class, ServiceNames
        from apps.albums.services.album_service import AlbumService
        from apps.albums.dal import AlbumDAL
        
        # Update service classes now that they're imported
        update_service_class(ServiceNames.ALBUM_SERVICE, AlbumService)
        update_service_class(ServiceNames.ALBUM_DAL, AlbumDAL)
