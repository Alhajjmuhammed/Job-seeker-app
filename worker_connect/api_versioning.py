"""
API versioning utilities for Worker Connect.

This module provides tools for managing API versions, deprecation notices,
and version-aware routing.
"""

from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
import warnings
from datetime import datetime


# API Version Configuration
API_VERSIONS = {
    'v1': {
        'status': 'current',
        'released': '2024-01-01',
        'deprecated': None,
        'sunset': None,
    },
    'v2': {
        'status': 'beta',
        'released': '2025-06-01',
        'deprecated': None,
        'sunset': None,
    },
}

CURRENT_API_VERSION = 'v1'
DEFAULT_API_VERSION = 'v1'


class APIVersion:
    """
    API version descriptor.
    """
    def __init__(self, version, status='current', released=None, 
                 deprecated=None, sunset=None):
        self.version = version
        self.status = status  # 'current', 'deprecated', 'sunset', 'beta'
        self.released = released
        self.deprecated = deprecated
        self.sunset = sunset
    
    @property
    def is_deprecated(self):
        return self.status == 'deprecated' or self.deprecated is not None
    
    @property
    def is_sunset(self):
        if self.sunset:
            return datetime.now().date() >= datetime.strptime(self.sunset, '%Y-%m-%d').date()
        return False
    
    def get_deprecation_message(self):
        if self.is_sunset:
            return f"API version {self.version} has been sunset and is no longer available."
        if self.is_deprecated:
            msg = f"API version {self.version} is deprecated."
            if self.sunset:
                msg += f" It will be sunset on {self.sunset}."
            return msg
        return None


def get_api_version(request):
    """
    Extract API version from request.
    
    Checks in order:
    1. URL path (e.g., /api/v1/...)
    2. Accept header (e.g., Accept: application/vnd.workerconnect.v1+json)
    3. Query parameter (e.g., ?api_version=v1)
    4. Custom header (e.g., X-API-Version: v1)
    """
    # From URL path
    path = request.path
    for version in API_VERSIONS.keys():
        if f'/api/{version}/' in path:
            return version
    
    # From Accept header
    accept = request.META.get('HTTP_ACCEPT', '')
    if 'application/vnd.workerconnect.' in accept:
        for version in API_VERSIONS.keys():
            if f'vnd.workerconnect.{version}' in accept:
                return version
    
    # From query parameter
    version = request.GET.get('api_version')
    if version in API_VERSIONS:
        return version
    
    # From custom header
    version = request.META.get('HTTP_X_API_VERSION')
    if version in API_VERSIONS:
        return version
    
    return DEFAULT_API_VERSION


class APIVersionMiddleware:
    """
    Middleware to handle API versioning and deprecation notices.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only process API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Get API version
        version = get_api_version(request)
        request.api_version = version
        
        # Check if version is valid
        if version not in API_VERSIONS:
            return JsonResponse({
                'error': 'Invalid API version',
                'message': f'API version {version} is not supported.',
                'supported_versions': list(API_VERSIONS.keys()),
            }, status=400)
        
        version_info = API_VERSIONS[version]
        api_version = APIVersion(version, **version_info)
        
        # Check if version is sunset
        if api_version.is_sunset:
            return JsonResponse({
                'error': 'API version sunset',
                'message': api_version.get_deprecation_message(),
                'current_version': CURRENT_API_VERSION,
            }, status=410)  # 410 Gone
        
        # Process request
        response = self.get_response(request)
        
        # Add version headers
        response['X-API-Version'] = version
        response['X-API-Current-Version'] = CURRENT_API_VERSION
        
        # Add deprecation headers if applicable
        if api_version.is_deprecated:
            response['X-API-Deprecated'] = 'true'
            response['X-API-Deprecation-Notice'] = api_version.get_deprecation_message()
            if api_version.sunset:
                response['X-API-Sunset'] = api_version.sunset
            response['Warning'] = f'299 - "API version {version} is deprecated"'
        
        return response


def deprecated_endpoint(sunset_date=None, alternative=None):
    """
    Decorator to mark an endpoint as deprecated.
    
    Usage:
        @deprecated_endpoint(sunset_date='2025-06-01', alternative='/api/v2/new-endpoint/')
        def old_endpoint(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            
            # Add deprecation headers
            if hasattr(response, '__setitem__'):
                response['X-Deprecated'] = 'true'
                
                msg = 'This endpoint is deprecated.'
                if sunset_date:
                    msg += f' It will be removed on {sunset_date}.'
                    response['X-Sunset'] = sunset_date
                if alternative:
                    msg += f' Use {alternative} instead.'
                    response['X-Alternative'] = alternative
                
                response['Warning'] = f'299 - "{msg}"'
            
            return response
        return wrapper
    return decorator


def version_aware(versions=None):
    """
    Decorator to make endpoint version-aware.
    
    Usage:
        @version_aware(versions=['v1', 'v2'])
        def my_endpoint(request):
            if request.api_version == 'v2':
                return new_behavior()
            return old_behavior()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if versions and hasattr(request, 'api_version'):
                if request.api_version not in versions:
                    return Response({
                        'error': 'Endpoint not available in this API version',
                        'available_versions': versions,
                    }, status=status.HTTP_404_NOT_FOUND)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


class VersionedSerializer:
    """
    Base class for version-aware serializers.
    
    Usage:
        class MySerializer(VersionedSerializer):
            v1_fields = ['id', 'name', 'created_at']
            v2_fields = ['id', 'name', 'created_at', 'updated_at', 'metadata']
            
            def get_v1_data(self, obj):
                return {...}
            
            def get_v2_data(self, obj):
                return {...}
    """
    v1_fields = []
    v2_fields = []
    
    def __init__(self, instance, version='v1', many=False):
        self.instance = instance
        self.version = version
        self.many = many
    
    @property
    def data(self):
        if self.many:
            return [self._serialize(obj) for obj in self.instance]
        return self._serialize(self.instance)
    
    def _serialize(self, obj):
        method_name = f'get_{self.version}_data'
        if hasattr(self, method_name):
            return getattr(self, method_name)(obj)
        return self.get_default_data(obj)
    
    def get_default_data(self, obj):
        """Override this for default serialization."""
        return {}


# API Version info endpoint
def api_version_info(request):
    """
    Return information about API versions.
    """
    versions = {}
    for version, info in API_VERSIONS.items():
        versions[version] = {
            'status': info['status'],
            'released': info['released'],
            'deprecated': info['deprecated'],
            'sunset': info['sunset'],
            'is_current': version == CURRENT_API_VERSION,
        }
    
    return JsonResponse({
        'current_version': CURRENT_API_VERSION,
        'default_version': DEFAULT_API_VERSION,
        'versions': versions,
        'versioning_methods': [
            'URL path: /api/v1/...',
            'Accept header: application/vnd.workerconnect.v1+json',
            'Query parameter: ?api_version=v1',
            'Custom header: X-API-Version: v1',
        ],
    })
