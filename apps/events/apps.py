from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Configuration for the Events application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.events'
    verbose_name = 'Events Management'

    # Simple Django app config without enterprise patterns
