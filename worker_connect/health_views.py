"""
Health check API views for monitoring and load balancer checks.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import logging
import time
import sys
import django

logger = logging.getLogger('api')


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
        
        return HealthCheckResult(
            name='database',
            healthy=True,
            message='Database connection successful',
            latency_ms=latency,
            details={'type': connection.vendor}
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
        test_key = '_health_check_test'
        test_value = str(time.time())
        
        cache.set(test_key, test_value, timeout=10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved != test_value:
            raise ValueError("Cache read/write verification failed")
        
        latency = (time.time() - start) * 1000
        
        cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        
        return HealthCheckResult(
            name='cache',
            healthy=True,
            message='Cache connection successful',
            latency_ms=latency,
            details={'backend': cache_backend.split('.')[-1]}
        )
    except Exception as e:
        return HealthCheckResult(
            name='cache',
            healthy=True,  # Cache is optional
            message=f'Cache not configured: {str(e)}',
            details={'configured': False}
        )


def check_celery():
    """Check Celery worker availability."""
    start = time.time()
    try:
        from worker_connect.celery import app as celery_app
        
        inspect = celery_app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        
        latency = (time.time() - start) * 1000
        
        if stats:
            return HealthCheckResult(
                name='celery',
                healthy=True,
                message=f'{len(stats)} worker(s) active',
                latency_ms=latency,
                details={'workers': list(stats.keys())}
            )
        else:
            return HealthCheckResult(
                name='celery',
                healthy=True,  # Celery is optional
                message='No Celery workers available',
                latency_ms=latency,
                details={'configured': True, 'workers_active': False}
            )
    except ImportError:
        return HealthCheckResult(
            name='celery',
            healthy=True,
            message='Celery not configured',
            details={'configured': False}
        )
    except Exception as e:
        return HealthCheckResult(
            name='celery',
            healthy=True,  # Celery is optional
            message=f'Celery check skipped: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def check_storage():
    """Check file storage accessibility."""
    start = time.time()
    try:
        import os
        
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        
        if media_root and os.path.exists(media_root):
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
            details={'writable': writable}
        )
    except Exception as e:
        return HealthCheckResult(
            name='storage',
            healthy=False,
            message=f'Storage check failed: {str(e)}',
            latency_ms=(time.time() - start) * 1000,
        )


def get_system_info():
    """Get system information."""
    info = {
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'django_version': f"{django.VERSION[0]}.{django.VERSION[1]}.{django.VERSION[2]}",
        'environment': getattr(settings, 'ENVIRONMENT', 'development'),
        'debug': settings.DEBUG,
    }
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        info['memory'] = {
            'total_mb': round(memory.total / (1024 * 1024), 2),
            'available_mb': round(memory.available / (1024 * 1024), 2),
            'percent_used': memory.percent,
        }
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
    Used by load balancers and monitoring services.
    """
    return Response({
        'status': 'healthy',
        'service': 'worker-connect-api',
        'timestamp': time.time(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check_detailed(request):
    """
    Detailed health check endpoint.
    
    Checks:
    - Database connectivity
    - Cache connectivity (if configured)
    - Celery workers (if configured)
    - Storage accessibility
    - Response time
    
    Returns 200 if all critical checks pass, 503 if critical checks fail.
    """
    start_time = time.time()
    
    # Run all health checks
    checks = [
        check_database(),
        check_cache(),
        check_celery(),
        check_storage(),
    ]
    
    # Database is critical, others are optional
    all_healthy = all(c.healthy for c in checks)
    critical_healthy = all(c.healthy for c in checks if c.name in ['database'])
    
    # Build response
    response_data = {
        'status': 'healthy' if all_healthy else ('degraded' if critical_healthy else 'unhealthy'),
        'service': 'worker-connect-api',
        'timestamp': time.time(),
        'response_time_ms': round((time.time() - start_time) * 1000, 2),
        'checks': [c.to_dict() for c in checks],
    }
    
    # Include system info for authenticated admin users
    if request.user.is_authenticated and request.user.is_staff:
        response_data['system'] = get_system_info()
    
    if critical_healthy:
        return Response(response_data)
    else:
        return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    
    Returns 200 when the service is ready to accept traffic.
    Returns 503 when the service is starting up or shutting down.
    """
    try:
        # Check database is accessible
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        
        return Response({
            'status': 'ready',
            'service': 'worker-connect-api'
        })
    except Exception as e:
        logger.warning(f"Readiness check failed: {str(e)}")
        return Response(
            {
                'status': 'not_ready',
                'error': 'Database not accessible'
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Liveness check endpoint for Kubernetes/container orchestration.
    
    Returns 200 if the service is alive and responding.
    This is a simple check that doesn't verify dependencies.
    """
    return Response({
        'status': 'alive',
        'service': 'worker-connect-api'
    })
