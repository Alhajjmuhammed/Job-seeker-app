from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_choice, name='register_choice'),
    path('register/worker/', views.worker_register, name='worker_register'),
    path('register/client/', views.client_register, name='client_register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    # Password Management
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Notification Center
    path('notifications/', views.notification_center, name='notification_center'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read_web, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read_web, name='mark_all_read'),
]
