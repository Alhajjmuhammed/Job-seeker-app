"""
Welcome e-mail for every new worker, client or agent, however they signed up
(website, app, or an agent creating a worker). send_welcome_email existed but
nothing ever called it.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)

WELCOMED_TYPES = ('worker', 'client', 'agent')


@receiver(post_save, sender=User)
def welcome_new_user(sender, instance, created, raw=False, **kwargs):
    if not created or raw or instance.user_type not in WELCOMED_TYPES or not instance.email:
        return

    def send():
        from workers.tasks import send_welcome_email
        try:
            # Celery sends it in the background so sign-up stays fast
            send_welcome_email.delay(instance.id, instance.user_type)
        except Exception as e:
            logger.warning("Queueing welcome email failed (%s); sending directly", e)
            send_welcome_email(instance.id, instance.user_type)

    # after the sign-up is saved, so the task can load the user
    transaction.on_commit(send)
