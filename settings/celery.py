"""Celery configuration for media_flow project."""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.main')

app = Celery('media_flow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery with secure defaults
app.conf.update(
    # Security settings
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Task routing and execution
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=True,
    
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Serialization settings (JSON for security)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone settings
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    
    # Beat scheduler settings
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')


# Health check task
@app.task(bind=True)
def health_check(self):
    """Health check task for monitoring."""
    return {'status': 'healthy', 'worker_id': self.request.id}