from django.urls import path
from .api_views import (
    login_view, register_view, logout_view, current_user_view, csrf_token_view,
    password_reset_request, password_reset_confirm, change_password,
    get_active_sessions, revoke_session, revoke_all_sessions, get_account_activity,
    get_notifications, mark_notification_read, mark_all_notifications_read, unread_notification_count
)

urlpatterns = [
    path('auth/login/', login_view, name='api_login'),
    path('auth/register/', register_view, name='api_register'),
    path('auth/logout/', logout_view, name='api_logout'),
    path('auth/user/', current_user_view, name='api_current_user'),
    path('auth/csrf/', csrf_token_view, name='api_csrf_token'),
    path('auth/password-reset/', password_reset_request, name='api_password_reset_request'),
    path('auth/password-reset/confirm/', password_reset_confirm, name='api_password_reset_confirm'),
    path('auth/change-password/', change_password, name='api_change_password'),
    # Session management
    path('auth/sessions/', get_active_sessions, name='api_active_sessions'),
    path('auth/sessions/revoke/', revoke_session, name='api_revoke_session'),
    path('auth/sessions/revoke-all/', revoke_all_sessions, name='api_revoke_all_sessions'),
    path('auth/activity/', get_account_activity, name='api_account_activity'),
    # Notifications
    path('notifications/', get_notifications, name='api_get_notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='api_mark_notification_read'),
    path('notifications/read-all/', mark_all_notifications_read, name='api_mark_all_notifications_read'),
    path('notifications/unread-count/', unread_notification_count, name='api_unread_notification_count'),
]
