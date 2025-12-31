"""
URL routes for notification preferences.
"""

from django.urls import path
from . import notification_views

urlpatterns = [
    path('', notification_views.get_notification_preferences, name='get_notification_prefs'),
    path('update/', notification_views.update_notification_preferences, name='update_notification_prefs'),
    path('mute/', notification_views.mute_notifications, name='mute_notifications'),
    path('unmute/', notification_views.unmute_notifications, name='unmute_notifications'),
    path('quiet-hours/', notification_views.set_quiet_hours, name='set_quiet_hours'),
    path('frequency/', notification_views.set_email_frequency, name='set_email_frequency'),
]
