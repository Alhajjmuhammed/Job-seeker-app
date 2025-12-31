"""
Caching utilities for Worker Connect.

Provides Redis-based caching with fallback to local memory cache.
"""

import logging
import hashlib
import json
from functools import wraps
from typing import Any, Optional, Callable
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache timeout constants (in seconds)
CACHE_TIMEOUT_SHORT = 60  # 1 minute
CACHE_TIMEOUT_MEDIUM = 300  # 5 minutes
CACHE_TIMEOUT_LONG = 3600  # 1 hour
CACHE_TIMEOUT_DAY = 86400  # 24 hours


def make_cache_key(*args, prefix: str = 'wc') -> str:
    """
    Generate a consistent cache key from arguments.
    
    Args:
        *args: Values to include in the key
        prefix: Key prefix (default: 'wc' for worker connect)
        
    Returns:
        str: Cache key
    """
    key_parts = [str(arg) for arg in args]
    key_string = ':'.join(key_parts)
    
    # Hash if too long
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f'{prefix}:{key_hash}'
    
    return f'{prefix}:{key_string}'


def cached(timeout: int = CACHE_TIMEOUT_MEDIUM, key_prefix: str = ''):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Optional prefix for cache key
        
    Usage:
        @cached(timeout=300, key_prefix='user')
        def get_user_stats(user_id):
            # expensive computation
            return stats
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f'{k}={v}' for k, v in sorted(kwargs.items()))
            cache_key = make_cache_key(*key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f'Cache hit: {cache_key}')
                return result
            
            # Execute function and cache result
            logger.debug(f'Cache miss: {cache_key}')
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def cache_page_api(timeout: int = CACHE_TIMEOUT_MEDIUM, key_func: Optional[Callable] = None):
    """
    Decorator to cache API view responses.
    
    Args:
        timeout: Cache timeout in seconds
        key_func: Optional function to generate cache key from request
        
    Usage:
        @api_view(['GET'])
        @cache_page_api(timeout=300)
        def my_view(request):
            return Response(data)
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip caching for non-GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                # Default key includes path and query params
                query_string = request.META.get('QUERY_STRING', '')
                cache_key = make_cache_key(
                    'api',
                    request.path,
                    query_string,
                    prefix='api_cache'
                )
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f'API cache hit: {cache_key}')
                return cached_response
            
            # Execute view and cache response
            response = view_func(request, *args, **kwargs)
            
            # Only cache successful responses
            if response.status_code == 200:
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


class CacheManager:
    """
    Manager class for cache operations.
    """
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return cache.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any, timeout: int = CACHE_TIMEOUT_MEDIUM) -> bool:
        """Set value in cache."""
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.error(f'Cache set error: {e}')
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """Delete value from cache."""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f'Cache delete error: {e}')
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """Delete all keys matching pattern (Redis only)."""
        try:
            # This only works with Redis backend
            if hasattr(cache, 'delete_pattern'):
                return cache.delete_pattern(pattern)
            logger.warning('delete_pattern not supported by cache backend')
            return 0
        except Exception as e:
            logger.error(f'Cache delete_pattern error: {e}')
            return 0
    
    @staticmethod
    def clear() -> bool:
        """Clear entire cache."""
        try:
            cache.clear()
            return True
        except Exception as e:
            logger.error(f'Cache clear error: {e}')
            return False
    
    @staticmethod
    def get_or_set(key: str, default_func: Callable, timeout: int = CACHE_TIMEOUT_MEDIUM) -> Any:
        """
        Get value from cache, or set it using default_func if not found.
        
        Args:
            key: Cache key
            default_func: Function to call if key not in cache
            timeout: Cache timeout
            
        Returns:
            Cached or computed value
        """
        value = cache.get(key)
        if value is None:
            value = default_func()
            if value is not None:
                cache.set(key, value, timeout)
        return value


# Common cache key patterns
class CacheKeys:
    """Pre-defined cache key patterns."""
    
    @staticmethod
    def user_profile(user_id: int) -> str:
        return make_cache_key('user', 'profile', user_id)
    
    @staticmethod
    def worker_profile(worker_id: int) -> str:
        return make_cache_key('worker', 'profile', worker_id)
    
    @staticmethod
    def job_detail(job_id: int) -> str:
        return make_cache_key('job', 'detail', job_id)
    
    @staticmethod
    def job_list(page: int = 1, filters: str = '') -> str:
        return make_cache_key('job', 'list', page, filters)
    
    @staticmethod
    def user_stats(user_id: int) -> str:
        return make_cache_key('user', 'stats', user_id)
    
    @staticmethod
    def dashboard_overview() -> str:
        return make_cache_key('admin', 'dashboard', 'overview')
    
    @staticmethod
    def search_results(query: str, page: int = 1) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return make_cache_key('search', query_hash, page)


# Cache invalidation helpers
def invalidate_user_cache(user_id: int):
    """Invalidate all cache entries for a user."""
    keys_to_delete = [
        CacheKeys.user_profile(user_id),
        CacheKeys.user_stats(user_id),
    ]
    for key in keys_to_delete:
        CacheManager.delete(key)


def invalidate_job_cache(job_id: int):
    """Invalidate cache for a job."""
    CacheManager.delete(CacheKeys.job_detail(job_id))
    # Also invalidate list caches (could be more sophisticated)
    CacheManager.delete_pattern('wc:job:list:*')


def invalidate_dashboard_cache():
    """Invalidate admin dashboard cache."""
    CacheManager.delete(CacheKeys.dashboard_overview())
