"""Shared app configuration."""

from django.apps import AppConfig


class SharedConfig(AppConfig):
    """Configuration for the Shared app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shared"
    verbose_name = "Shared"
