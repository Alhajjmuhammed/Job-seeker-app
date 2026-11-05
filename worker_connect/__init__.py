# This makes the worker_connect directory a Python package.
#
# Load the Celery app with Django, so .delay() from the website uses the
# configured broker. Without this, every task queued by a web request went
# to Celery's built-in default (amqp://localhost), failed, and fell back.
from .celery import app as celery_app

__all__ = ('celery_app',)
