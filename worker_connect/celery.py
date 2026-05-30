"""
Celery configuration for Worker Connect background tasks.

This module configures Celery for asynchronous task processing.
"""

import os
from celery import Celery
from django.conf import settings

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')

# Create Celery app
app = Celery('worker_connect')

# Configure Celery from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery configuration
app.conf.update(
    # Broker settings (Redis)
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task result expiration
    result_expires=3600,  # 1 hour
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Rate limiting
    task_default_rate_limit='100/m',
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_concurrency=4,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'check-overdue-invoices': {
            'task': 'jobs.tasks.check_overdue_invoices',
            'schedule': 3600.0,  # Every hour
        },
        'send-job-reminders': {
            'task': 'jobs.tasks.send_job_reminders',
            'schedule': 86400.0,  # Daily
        },
        'cleanup-old-activities': {
            'task': 'jobs.tasks.cleanup_old_activities',
            'schedule': 86400.0,  # Daily
        },
        'warm-cache': {
            'task': 'worker_connect.tasks.warm_cache',
            'schedule': 1800.0,  # Every 30 minutes
        },
        'update-worker-ratings': {
            'task': 'workers.tasks.update_worker_ratings',
            'schedule': 3600.0,  # Every hour
        },
        'check-badge-expirations': {
            'task': 'workers.tasks.check_badge_expirations',
            'schedule': 86400.0,  # Daily
        },
    },
)

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
