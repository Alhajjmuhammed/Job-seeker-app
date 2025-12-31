"""
Rate limit middleware for adding rate limit headers to responses.
"""

import time
from django.conf import settings
from django.core.cache import cache


class RateLimitHeadersMiddleware:
    """
    Middleware to add rate limit headers to API responses.
    
    Headers added:
        - X-RateLimit-Limit: Maximum requests allowed in window
        - X-RateLimit-Remaining: Requests remaining in current window
        - X-RateLimit-Reset: Unix timestamp when the window resets
        - X-RateLimit-Window: Window duration in seconds
        - Retry-After: Seconds until rate limit resets (when limited)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.default_limit = getattr(settings, 'RATE_LIMIT_DEFAULT', 100)
        self.default_window = getattr(settings, 'RATE_LIMIT_WINDOW', 3600)  # 1 hour
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Only add headers for API endpoints
        if not self._is_api_request(request):
            return response
        
        # Get rate limit info
        rate_info = self._get_rate_limit_info(request)
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = rate_info['limit']
        response['X-RateLimit-Remaining'] = max(0, rate_info['remaining'])
        response['X-RateLimit-Reset'] = rate_info['reset_time']
        response['X-RateLimit-Window'] = rate_info['window']
        
        # Add Retry-After if rate limited
        if rate_info['remaining'] <= 0:
            response['Retry-After'] = rate_info['retry_after']
        
        return response
    
    def _is_api_request(self, request):
        """Check if request is to API endpoint."""
        return request.path.startswith('/api/')
    
    def _get_client_id(self, request):
        """Get unique identifier for the client."""
        # Use authenticated user ID if available
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        return f"ip:{ip}"
    
    def _get_rate_limit_info(self, request):
        """
        Get rate limit information for the current request.
        """
        client_id = self._get_client_id(request)
        cache_key = f"ratelimit:{client_id}"
        
        # Get current time
        current_time = int(time.time())
        
        # Get rate limit settings for this endpoint
        limit, window = self._get_endpoint_limits(request)
        
        # Get current rate limit data from cache
        rate_data = cache.get(cache_key)
        
        if rate_data is None:
            # No existing rate limit data
            window_start = current_time
            request_count = 1
        else:
            window_start = rate_data.get('window_start', current_time)
            request_count = rate_data.get('count', 0)
            
            # Check if window has expired
            if current_time - window_start >= window:
                # Reset window
                window_start = current_time
                request_count = 1
            else:
                request_count += 1
        
        # Calculate reset time
        reset_time = window_start + window
        retry_after = max(0, reset_time - current_time)
        
        # Update cache
        cache.set(cache_key, {
            'window_start': window_start,
            'count': request_count,
        }, timeout=window)
        
        return {
            'limit': limit,
            'remaining': limit - request_count,
            'reset_time': reset_time,
            'window': window,
            'retry_after': retry_after,
        }
    
    def _get_endpoint_limits(self, request):
        """
        Get rate limits for specific endpoint.
        Override this for custom per-endpoint limits.
        """
        # Endpoint-specific limits
        endpoint_limits = getattr(settings, 'RATE_LIMIT_ENDPOINTS', {})
        
        path = request.path
        
        # Check for matching endpoint
        for pattern, limits in endpoint_limits.items():
            if pattern in path:
                return limits.get('limit', self.default_limit), limits.get('window', self.default_window)
        
        # Different limits for authenticated vs anonymous
        if request.user.is_authenticated:
            auth_limit = getattr(settings, 'RATE_LIMIT_AUTHENTICATED', self.default_limit * 2)
            return auth_limit, self.default_window
        
        # Anonymous users get default limit
        anon_limit = getattr(settings, 'RATE_LIMIT_ANONYMOUS', self.default_limit)
        return anon_limit, self.default_window


class RateLimitExceededMiddleware:
    """
    Middleware to check rate limits and return 429 Too Many Requests.
    Should be used with RateLimitHeadersMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        from django.http import JsonResponse
        
        # Skip non-API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Check rate limit
        if self._is_rate_limited(request):
            response = JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
            }, status=429)
            
            # Get retry info
            rate_info = self._get_rate_info(request)
            response['Retry-After'] = rate_info.get('retry_after', 60)
            
            return response
        
        return self.get_response(request)
    
    def _get_client_id(self, request):
        """Get unique identifier for the client."""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        return f"ip:{ip}"
    
    def _is_rate_limited(self, request):
        """Check if client has exceeded rate limit."""
        client_id = self._get_client_id(request)
        cache_key = f"ratelimit:{client_id}"
        
        rate_data = cache.get(cache_key)
        if not rate_data:
            return False
        
        limit = getattr(settings, 'RATE_LIMIT_DEFAULT', 100)
        if request.user.is_authenticated:
            limit = getattr(settings, 'RATE_LIMIT_AUTHENTICATED', limit * 2)
        
        return rate_data.get('count', 0) > limit
    
    def _get_rate_info(self, request):
        """Get rate limit info for response headers."""
        client_id = self._get_client_id(request)
        cache_key = f"ratelimit:{client_id}"
        
        rate_data = cache.get(cache_key, {})
        current_time = int(time.time())
        window = getattr(settings, 'RATE_LIMIT_WINDOW', 3600)
        window_start = rate_data.get('window_start', current_time)
        
        return {
            'retry_after': max(0, (window_start + window) - current_time)
        }
