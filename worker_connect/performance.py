"""
Performance monitoring for Worker Connect.

Tracks response times, database queries, and system metrics.
"""

import time
import logging
import functools
from typing import Dict, Any, Callable, Optional
from django.db import connection, reset_queries
from django.conf import settings

logger = logging.getLogger('performance')


class PerformanceMetrics:
    """
    Singleton for tracking performance metrics.
    """
    
    _instance = None
    _metrics: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {
                'requests': [],
                'slow_queries': [],
                'errors': [],
                'endpoint_stats': {},
            }
        return cls._instance
    
    def record_request(
        self,
        path: str,
        method: str,
        response_time: float,
        status_code: int,
        query_count: int = 0
    ):
        """Record a request metric."""
        entry = {
            'timestamp': time.time(),
            'path': path,
            'method': method,
            'response_time_ms': round(response_time * 1000, 2),
            'status_code': status_code,
            'query_count': query_count,
        }
        
        # Keep last 1000 requests
        self._metrics['requests'].append(entry)
        if len(self._metrics['requests']) > 1000:
            self._metrics['requests'] = self._metrics['requests'][-1000:]
        
        # Update endpoint stats
        endpoint_key = f"{method}:{path}"
        if endpoint_key not in self._metrics['endpoint_stats']:
            self._metrics['endpoint_stats'][endpoint_key] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'errors': 0,
            }
        
        stats = self._metrics['endpoint_stats'][endpoint_key]
        stats['count'] += 1
        stats['total_time'] += response_time * 1000
        stats['min_time'] = min(stats['min_time'], response_time * 1000)
        stats['max_time'] = max(stats['max_time'], response_time * 1000)
        
        if status_code >= 400:
            stats['errors'] += 1
        
        # Log slow requests
        if response_time > 1.0:  # > 1 second
            logger.warning(
                f"Slow request: {method} {path} - {response_time * 1000:.2f}ms"
            )
    
    def record_slow_query(self, query: str, time_ms: float):
        """Record a slow database query."""
        entry = {
            'timestamp': time.time(),
            'query': query[:500],  # Truncate long queries
            'time_ms': round(time_ms, 2),
        }
        
        self._metrics['slow_queries'].append(entry)
        if len(self._metrics['slow_queries']) > 100:
            self._metrics['slow_queries'] = self._metrics['slow_queries'][-100:]
        
        logger.warning(f"Slow query ({time_ms:.2f}ms): {query[:200]}")
    
    def record_error(self, error_type: str, message: str, path: str = ''):
        """Record an error."""
        entry = {
            'timestamp': time.time(),
            'type': error_type,
            'message': message[:500],
            'path': path,
        }
        
        self._metrics['errors'].append(entry)
        if len(self._metrics['errors']) > 500:
            self._metrics['errors'] = self._metrics['errors'][-500:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        requests = self._metrics['requests']
        
        if not requests:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'error_rate': 0,
            }
        
        recent_requests = requests[-100:]  # Last 100 requests
        
        total_time = sum(r['response_time_ms'] for r in recent_requests)
        error_count = sum(1 for r in recent_requests if r['status_code'] >= 400)
        
        return {
            'total_requests': len(requests),
            'recent_requests': len(recent_requests),
            'avg_response_time_ms': round(total_time / len(recent_requests), 2),
            'error_rate': round(error_count / len(recent_requests) * 100, 2),
            'slow_queries_count': len(self._metrics['slow_queries']),
            'errors_count': len(self._metrics['errors']),
        }
    
    def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get per-endpoint statistics."""
        stats = {}
        for endpoint, data in self._metrics['endpoint_stats'].items():
            if data['count'] > 0:
                stats[endpoint] = {
                    'count': data['count'],
                    'avg_time_ms': round(data['total_time'] / data['count'], 2),
                    'min_time_ms': round(data['min_time'], 2),
                    'max_time_ms': round(data['max_time'], 2),
                    'error_rate': round(data['errors'] / data['count'] * 100, 2),
                }
        return stats
    
    def get_slow_queries(self, limit: int = 20) -> list:
        """Get recent slow queries."""
        return self._metrics['slow_queries'][-limit:]
    
    def get_recent_errors(self, limit: int = 50) -> list:
        """Get recent errors."""
        return self._metrics['errors'][-limit:]
    
    def clear(self):
        """Clear all metrics."""
        self._metrics = {
            'requests': [],
            'slow_queries': [],
            'errors': [],
            'endpoint_stats': {},
        }


class PerformanceMiddleware:
    """
    Middleware for tracking request performance.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.metrics = PerformanceMetrics()
    
    def __call__(self, request):
        # Skip static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Track queries if DEBUG
        if settings.DEBUG:
            reset_queries()
        
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Count queries
        query_count = 0
        if settings.DEBUG:
            query_count = len(connection.queries)
            
            # Check for slow queries
            for query in connection.queries:
                query_time = float(query.get('time', 0)) * 1000
                if query_time > 100:  # > 100ms
                    self.metrics.record_slow_query(query['sql'], query_time)
        
        # Record metrics
        self.metrics.record_request(
            path=request.path,
            method=request.method,
            response_time=response_time,
            status_code=response.status_code,
            query_count=query_count,
        )
        
        # Add performance headers in debug mode
        if settings.DEBUG:
            response['X-Response-Time'] = f"{response_time * 1000:.2f}ms"
            response['X-Query-Count'] = str(query_count)
        
        return response


def track_performance(func: Callable = None, name: str = None):
    """
    Decorator for tracking function performance.
    
    Usage:
        @track_performance
        def my_function():
            pass
        
        @track_performance(name='custom_name')
        def my_function():
            pass
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                func_name = name or f.__name__
                
                if elapsed > 0.5:  # > 500ms
                    logger.warning(
                        f"Slow function: {func_name} - {elapsed * 1000:.2f}ms"
                    )
                else:
                    logger.debug(
                        f"Function {func_name} completed in {elapsed * 1000:.2f}ms"
                    )
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def get_system_metrics() -> Dict[str, Any]:
    """Get system-level metrics."""
    import os
    import psutil
    
    try:
        process = psutil.Process(os.getpid())
        
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory': {
                'total_mb': round(psutil.virtual_memory().total / 1024 / 1024, 2),
                'available_mb': round(psutil.virtual_memory().available / 1024 / 1024, 2),
                'percent': psutil.virtual_memory().percent,
                'process_mb': round(process.memory_info().rss / 1024 / 1024, 2),
            },
            'disk': {
                'total_gb': round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                'free_gb': round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2),
                'percent': psutil.disk_usage('/').percent,
            },
            'connections': len(process.connections()),
            'open_files': len(process.open_files()),
            'threads': process.num_threads(),
        }
    except ImportError:
        return {
            'error': 'psutil not installed',
            'message': 'Install psutil for system metrics: pip install psutil'
        }
    except Exception as e:
        return {'error': str(e)}


def get_database_metrics() -> Dict[str, Any]:
    """Get database metrics."""
    from django.db import connection
    
    metrics = {
        'vendor': connection.vendor,
        'queries_this_request': len(connection.queries) if settings.DEBUG else 'N/A (DEBUG=False)',
    }
    
    # Try to get connection pool info if using django-db-connection-pool
    try:
        pool = getattr(connection, 'pool', None)
        if pool:
            metrics['pool'] = {
                'size': pool.size(),
                'checkedin': pool.checkedin(),
                'checkedout': pool.checkedout(),
            }
    except:
        pass
    
    return metrics
