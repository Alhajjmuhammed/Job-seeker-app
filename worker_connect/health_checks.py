"""
Comprehensive health check endpoints for Worker Connect.

Provides detailed health status for all system dependencies.
"""

import time
import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(self, name, healthy=True, message="OK", latency_ms=None, details=None):
        self.name = name
        self.healthy = healthy
        self.message = message
        self.latency_ms = latency_ms
        self.details = details or {}
    
    def to_dict(self):
        result = {
            'name': self.name,
            'status': 'healthy' if self.healthy else 'unhealthy',
            'message': self.message,
        }
        if self.latency_ms is not None:
            result['latency_ms'] = round(self.latency_ms, 2)
        if self.details:
            result['details'] = self.details
        return result


def check_database():
    """Check database connectivity and response time."""
    start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        
        latency = (time.time() - start) * 1000
        
        # Get database info
        db_settings = settings.DATABASES.get('default', {})
        db_engine = db_settings.get('ENGINE', 'unknown')
        
        return HealthCheckResult(
            name='database',
            healthy=True,
            message='Database connection successful',
            latency_ms=latency,
            details={
                'engine': db_engine.split('.')[-1],
            }
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return HealthCheckResult(
            name='database',
            healthy=False,
            message=f'Database connection failed: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def check_cache():
    """Check cache (Redis) connectivity."""
    start = time.time()
    try:
        # Try to set and get a test value
        test_key = '_health_check_test'
        test_value = str(time.time())
        
        cache.set(test_key, test_value, timeout=10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved != test_value:
            raise ValueError("Cache read/write verification failed")
        
        latency = (time.time() - start) * 1000
        
        # Get cache backend info
        cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        
        return HealthCheckResult(
            name='cache',
            healthy=True,
            message='Cache connection successful',
            latency_ms=latency,
            details={
                'backend': cache_backend.split('.')[-1],
            }
        )
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return HealthCheckResult(
            name='cache',
            healthy=False,
            message=f'Cache connection failed: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def check_celery():
    """Check Celery worker availability."""
    start = time.time()
    try:
        from worker_connect.celery import app as celery_app
        
        # Check if we can inspect active workers
        inspect = celery_app.control.inspect()
        
        # Try to get stats (with timeout)
        stats = inspect.stats()
        
        latency = (time.time() - start) * 1000
        
        if stats:
            worker_count = len(stats)
            return HealthCheckResult(
                name='celery',
                healthy=True,
                message=f'{worker_count} worker(s) active',
                latency_ms=latency,
                details={
                    'workers': list(stats.keys()),
                }
            )
        else:
            return HealthCheckResult(
                name='celery',
                healthy=False,
                message='No Celery workers available',
                latency_ms=latency,
            )
    except ImportError:
        return HealthCheckResult(
            name='celery',
            healthy=True,
            message='Celery not configured',
            details={'configured': False}
        )
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return HealthCheckResult(
            name='celery',
            healthy=False,
            message=f'Celery check failed: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def check_storage():
    """Check file storage accessibility."""
    start = time.time()
    try:
        import os
        from django.core.files.storage import default_storage
        
        # Check if media directory is writable
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        
        if media_root and os.path.exists(media_root):
            # Try to create a test file
            test_path = os.path.join(media_root, '_health_check_test.txt')
            try:
                with open(test_path, 'w') as f:
                    f.write('test')
                os.remove(test_path)
                writable = True
            except Exception:
                writable = False
        else:
            writable = False
        
        latency = (time.time() - start) * 1000
        
        return HealthCheckResult(
            name='storage',
            healthy=writable,
            message='Storage accessible' if writable else 'Storage not writable',
            latency_ms=latency,
            details={
                'media_root': media_root,
                'writable': writable,
            }
        )
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return HealthCheckResult(
            name='storage',
            healthy=False,
            message=f'Storage check failed: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def check_email():
    """Check email backend configuration."""
    try:
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'unknown')
        email_host = getattr(settings, 'EMAIL_HOST', None)
        
        # For console backend in dev, always healthy
        if 'console' in email_backend.lower():
            return HealthCheckResult(
                name='email',
                healthy=True,
                message='Console email backend (development)',
                details={'backend': 'console'}
            )
        
        # For SMTP, check if host is configured
        if email_host:
            return HealthCheckResult(
                name='email',
                healthy=True,
                message='Email configured',
                details={
                    'backend': email_backend.split('.')[-1],
                    'host': email_host,
                }
            )
        else:
            return HealthCheckResult(
                name='email',
                healthy=False,
                message='Email host not configured',
            )
    except Exception as e:
        logger.error(f"Email health check failed: {e}")
        return HealthCheckResult(
            name='email',
            healthy=False,
            message=f'Email check failed: {str(e)}',
        )


def check_external_services():
    """Check connectivity to external services."""
    results = []
    
    # Add checks for any external APIs your app depends on
    # Example: payment gateway, SMS service, etc.
    
    return results


def get_system_info():
    """Get system information."""
    import os
    import sys
    import django
    
    info = {
        'python_version': sys.version,
        'django_version': django.VERSION,
        'environment': getattr(settings, 'ENVIRONMENT', 'development'),
        'debug': settings.DEBUG,
    }
    
    # Add memory info if psutil is available
    try:
        import psutil
        memory = psutil.virtual_memory()
        info['memory'] = {
            'total_mb': round(memory.total / (1024 * 1024), 2),
            'available_mb': round(memory.available / (1024 * 1024), 2),
            'percent_used': memory.percent,
        }
        
        # CPU info
        info['cpu'] = {
            'count': psutil.cpu_count(),
            'percent': psutil.cpu_percent(interval=0.1),
        }
    except ImportError:
        pass
    
    return info


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint.
    
    Returns 200 if the service is running.
    """
    return Response({
        'status': 'healthy',
        'service': 'Worker Connect API',
        'timestamp': time.time(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check_detailed(request):
    """
    Detailed health check endpoint.
    
    Returns status of all dependencies.
    """
    checks = [
        check_database(),
        check_cache(),
        check_celery(),
        check_storage(),
        check_email(),
    ]
    
    # Add any external service checks
    checks.extend(check_external_services())
    
    # Determine overall health
    all_healthy = all(check.healthy for check in checks)
    critical_healthy = all(
        check.healthy for check in checks 
        if check.name in ['database']  # Add other critical services
    )
    
    # Build response
    response_data = {
        'status': 'healthy' if all_healthy else ('degraded' if critical_healthy else 'unhealthy'),
        'timestamp': time.time(),
        'checks': [check.to_dict() for check in checks],
    }
    
    # Include system info for authenticated admin users
    if request.user.is_authenticated and request.user.is_staff:
        response_data['system'] = get_system_info()
    
    # Set appropriate status code
    if all_healthy:
        status_code = 200
    elif critical_healthy:
        status_code = 200  # Degraded but functional
    else:
        status_code = 503  # Service unavailable
    
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Kubernetes-style readiness probe.
    
    Returns 200 only if the service is ready to accept traffic.
    """
    # Check critical dependencies
    db_check = check_database()
    cache_check = check_cache()
    
    ready = db_check.healthy and cache_check.healthy
    
    return Response(
        {
            'ready': ready,
            'checks': {
                'database': db_check.healthy,
                'cache': cache_check.healthy,
            }
        },
        status=200 if ready else 503
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the service is alive (basic process check).
    """
    return Response({'alive': True}, status=200)


# URL patterns for health checks
from django.urls import path

health_urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('health/detailed/', health_check_detailed, name='health-check-detailed'),
    path('health/ready/', readiness_check, name='readiness-check'),
    path('health/live/', liveness_check, name='liveness-check'),
]
