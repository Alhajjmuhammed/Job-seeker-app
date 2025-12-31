"""
Mobile app configuration service for Worker Connect.

Provides remote configuration endpoint for app settings, feature flags,
and dynamic content that can be updated without app releases.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.core.cache import cache


# Default app configuration
DEFAULT_CONFIG = {
    # App version requirements
    'version': {
        'min_supported': '1.0.0',
        'current': '1.0.0',
        'force_update': False,
        'update_message': 'A new version is available. Please update for the best experience.',
    },
    
    # Feature flags
    'features': {
        'push_notifications': True,
        'in_app_messaging': True,
        'job_recommendations': True,
        'worker_ratings': True,
        'document_upload': True,
        'location_services': True,
        'dark_mode': True,
        'biometric_login': True,
        'social_login': False,
        'payment_integration': False,
    },
    
    # UI configuration
    'ui': {
        'primary_color': '#3498db',
        'secondary_color': '#2ecc71',
        'accent_color': '#e74c3c',
        'max_image_size_mb': 5,
        'max_document_size_mb': 10,
        'supported_image_formats': ['jpg', 'jpeg', 'png', 'webp'],
        'supported_document_formats': ['pdf', 'doc', 'docx'],
    },
    
    # API configuration
    'api': {
        'timeout_seconds': 30,
        'max_retries': 3,
        'page_size': 20,
        'max_page_size': 50,
    },
    
    # Business rules
    'rules': {
        'max_applications_per_job': 50,
        'max_active_jobs_per_client': 10,
        'max_photos_per_profile': 5,
        'min_password_length': 8,
        'session_timeout_minutes': 60,
        'refresh_token_days': 30,
    },
    
    # Content
    'content': {
        'support_email': 'support@workerconnect.com',
        'support_phone': '+1-800-WORKER',
        'terms_url': '/terms',
        'privacy_url': '/privacy',
        'faq_url': '/faq',
    },
    
    # Localization
    'localization': {
        'default_language': 'en',
        'supported_languages': ['en', 'es', 'fr'],
        'default_currency': 'USD',
        'date_format': 'YYYY-MM-DD',
        'time_format': '12h',
    },
    
    # Maintenance mode
    'maintenance': {
        'enabled': False,
        'message': 'We are currently performing maintenance. Please try again later.',
        'estimated_end': None,
    },
}


def get_app_config():
    """
    Get app configuration, with caching.
    Override defaults with any custom settings from Django settings.
    """
    cache_key = 'app_config'
    config = cache.get(cache_key)
    
    if config is None:
        config = DEFAULT_CONFIG.copy()
        
        # Override with any custom settings
        custom_config = getattr(settings, 'MOBILE_APP_CONFIG', {})
        for key, value in custom_config.items():
            if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value
        
        # Cache for 5 minutes
        cache.set(cache_key, config, 300)
    
    return config


@api_view(['GET'])
@permission_classes([AllowAny])
def app_config(request):
    """
    Get mobile app configuration.
    
    Query params:
        - version: Client app version (for version-specific config)
        - platform: 'ios' or 'android'
    """
    client_version = request.query_params.get('version', '1.0.0')
    platform = request.query_params.get('platform', 'unknown')
    
    config = get_app_config()
    
    # Add request-specific info
    config['request'] = {
        'client_version': client_version,
        'platform': platform,
        'server_time': request._request.META.get('HTTP_DATE', None),
    }
    
    # Check if update is required
    min_version = config['version']['min_supported']
    if compare_versions(client_version, min_version) < 0:
        config['version']['force_update'] = True
    
    return Response(config)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_status(request):
    """
    Simple health check for app to verify server connectivity.
    """
    return Response({
        'status': 'healthy',
        'maintenance': get_app_config()['maintenance']['enabled'],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_config(request):
    """
    Get user-specific configuration based on their profile.
    """
    user = request.user
    base_config = get_app_config()
    
    user_specific = {
        'user_type': user.user_type,
        'notifications': {
            'push_enabled': True,  # Would come from user preferences
            'email_enabled': True,
            'sms_enabled': False,
        },
        'preferences': {
            'language': 'en',  # Would come from user preferences
            'currency': 'USD',
            'timezone': 'UTC',
        },
    }
    
    # Worker-specific settings
    if user.user_type == 'worker' and hasattr(user, 'worker_profile'):
        profile = user.worker_profile
        user_specific['worker'] = {
            'profile_complete': profile.is_profile_complete,
            'is_verified': profile.is_verified,
            'is_available': profile.is_available,
            'can_apply_jobs': profile.is_profile_complete,
        }
    
    # Client-specific settings
    if user.user_type == 'client':
        user_specific['client'] = {
            'can_post_jobs': True,
            'max_active_jobs': base_config['rules']['max_active_jobs_per_client'],
        }
    
    return Response({
        'config': base_config,
        'user': user_specific,
    })


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        
        # Pad shorter version with zeros
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)
        
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0
    except (ValueError, AttributeError):
        return 0
