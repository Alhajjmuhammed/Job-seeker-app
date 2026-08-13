"""
worker_connect's models are defined across several files (notification_models.py,
support_models.py) rather than in this file directly. Django only
auto-discovers models that are actually imported into an app's models.py -
without this file, none of them were registered in the app registry at all
unless some unrelated import chain happened to import them first (e.g. a
view importing NotificationService). That made cascade-deletes silently
skip them (a real FK constraint violation when deleting a User with any
Notification/NotificationPreference/PushToken/SupportTicket/etc. row) and
made their registration depend on incidental, fragile import ordering.
Importing them here guarantees they're always registered, matching Django's
documented requirement for models defined outside of models.py.
"""
from .notification_models import Notification, NotificationPreference, PushToken  # noqa: E402,F401
from .support_models import SupportTicket, SupportMessage, FAQ  # noqa: E402,F401
