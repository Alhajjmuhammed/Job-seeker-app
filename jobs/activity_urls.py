"""
URL routes for activity feed.
"""

from django.urls import path
from . import activity_views

app_name = 'activity'

urlpatterns = [
    path('feed/', activity_views.get_my_feed, name='get_my_feed'),
    path('public/', activity_views.get_public_feed, name='get_public_feed'),
    path('types/', activity_views.get_activity_types, name='get_activity_types'),
    path('unread-count/', activity_views.get_unread_count, name='get_unread_count'),
    path('<int:activity_id>/read/', activity_views.mark_read, name='mark_read'),
    path('mark-all-read/', activity_views.mark_all_read, name='mark_all_read'),
]
