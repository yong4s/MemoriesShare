from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Configuration for the Events application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.events'
    verbose_name = 'Events Management'

    def ready(self):
        """
        Application ready hook.
        
        This method is called when Django has loaded all models and 
        the application is ready. We use it to register services
        with the shared factory.
        """
        # Register services with the service factory
        self._register_services()
        
        # Register EventPermissionService as the advanced validator
        from apps.shared.services.permission_factory import register_permission_service
        from apps.events.services.permission_service import EventPermissionService
        
        register_permission_service(EventPermissionService)
    
    def _register_services(self):
        """Register all event-related services with the service factory."""
        from apps.shared.services.service_factory import update_service_class, ServiceNames, register_default_services
        from apps.events.services.event_service import EventService
        from apps.events.services.permission_service import EventPermissionService
        from apps.events.dal.event_dal import EventDAL
        
        # Register default services if not already done
        try:
            register_default_services()
        except Exception:
            # Default services might already be registered
            pass
        
        # Import and register S3Service
        from apps.shared.storage.optimized_s3_service import OptimizedS3Service
        
        # Update service classes now that they're imported
        update_service_class(ServiceNames.EVENT_SERVICE, EventService)
        update_service_class(ServiceNames.PERMISSION_SERVICE, EventPermissionService)
        update_service_class(ServiceNames.EVENT_DAL, EventDAL)
        update_service_class(ServiceNames.S3_SERVICE, OptimizedS3Service)
