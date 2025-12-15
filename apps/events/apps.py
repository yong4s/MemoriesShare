from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Configuration for the Events application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    verbose_name = "Events Management"

    # Простий Django app config без enterprise паттернів
    # Вся логіка тепер в простих імпортах сервісів
