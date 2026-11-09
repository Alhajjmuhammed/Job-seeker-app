"""Background jobs for worker_connect (picked up by Celery autodiscovery)."""
from celery import shared_task


@shared_task(ignore_result=True)
def send_push_for_notification(notification_id):
    """Phone push for one Notification (see worker_connect/expo_push.py)."""
    from .expo_push import push_notification
    push_notification(notification_id)
