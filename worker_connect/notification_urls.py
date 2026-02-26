from django.urls import path
from . import notification_views

app_name = 'wc_notifications'

urlpatterns = [
    path('', notification_views.notification_list, name='list'),
    path('counts/', notification_views.notification_counts, name='counts'),
    path('<int:notification_id>/read/', notification_views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', notification_views.mark_all_read, name='mark_all_read'),
    path('<int:notification_id>/delete/', notification_views.delete_notification, name='delete'),
    path('preferences/', notification_views.notification_preferences, name='preferences'),
    path('push-token/register/', notification_views.register_push_token, name='register_push_token'),
    path('push-token/unregister/', notification_views.unregister_push_token, name='unregister_push_token'),
]