"""
URL routes for privacy settings.
"""

from django.urls import path
from . import privacy_views

urlpatterns = [
    path('', privacy_views.get_privacy_settings, name='get_privacy_settings'),
    path('update/', privacy_views.update_privacy_settings, name='update_privacy_settings'),
]
