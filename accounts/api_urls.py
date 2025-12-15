from django.urls import path
from .api_views import login_view, register_view, logout_view, current_user_view

urlpatterns = [
    path('auth/login/', login_view, name='api_login'),
    path('auth/register/', register_view, name='api_register'),
    path('auth/logout/', logout_view, name='api_logout'),
    path('auth/user/', current_user_view, name='api_current_user'),
]
