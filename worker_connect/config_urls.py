from django.urls import path
from . import app_config, config_views

app_name = 'wc_config'

urlpatterns = [
    # Root config API endpoint
    path('', app_config.app_config, name='config_root'),
    
    path('app/', app_config.app_config, name='app_config'),
    path('user/', app_config.user_config, name='user_config'),
    path('health/', app_config.health_status, name='health_status'),
    path('terms/', config_views.terms_of_service, name='terms'),
    path('privacy/', config_views.privacy_policy, name='privacy'),
    path('app-version/', config_views.app_version, name='app_version'),
    path('contact-info/', config_views.contact_info, name='contact_info'),
]
