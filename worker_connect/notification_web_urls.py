"""
URL patterns for notification center web interface
"""
from django.urls import path
from .notification_web_views import (
    notification_center,
    mark_notification_read_web,
    mark_all_read_web,
    delete_notification_web,
    get_unread_count,
)

urlpatterns = [
    # Main notification center page
    path('', notification_center, name='notification_center'),
    
    # Mark notifications as read
    path('<int:notification_id>/mark-read/', mark_notification_read_web, name='mark_notification_read_web'),
    path('mark-all-read/', mark_all_read_web, name='mark_all_read_web'),
    
    # Delete notification
    path('<int:notification_id>/delete/', delete_notification_web, name='delete_notification_web'),
    
    # AJAX endpoint for unread count
    path('unread-count/', get_unread_count, name='get_unread_count'),
]
