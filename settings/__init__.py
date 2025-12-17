"""Settings package initialization with Celery app."""

from settings.celery import app as celery_app

__all__ = ('celery_app',)
