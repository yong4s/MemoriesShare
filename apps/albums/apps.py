from django.apps import AppConfig


class AlbumsConfig(AppConfig):
    """Configuration for the Albums application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.albums'
    verbose_name = 'Albums Management'
