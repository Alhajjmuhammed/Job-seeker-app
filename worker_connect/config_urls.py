from django.urls import path
from . import app_config

app_name = 'config'

urlpatterns = [
    path('app/', app_config.app_config, name='app_config'),
    path('user/', app_config.user_config, name='user_config'),
    path('health/', app_config.health_status, name='health_status'),
]
