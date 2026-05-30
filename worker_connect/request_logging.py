"""
Request logging middleware for Worker Connect.

Provides detailed logging of API requests and responses for debugging and monitoring.
"""

import logging
import time
import json
import uuid
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('api.requests')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses.
    """
    
    # Paths to exclude from logging
    EXCLUDED_PATHS = [
        '/api/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
    ]
    
    # Sensitive fields to mask
    SENSITIVE_FIELDS = [
        'password',
        'token',
        'secret',
        'api_key',
        'authorization',
        'credit_card',
        'cvv',
        'ssn',
    ]
    
    # Maximum body size to log (bytes)
    MAX_BODY_SIZE = 10000
    
    def process_request(self, request):
        """Process incoming request."""
        # Generate request ID
        request.request_id = str(uuid.uuid4())[:8]
        
        # Record start time
        request._start_time = time.time()
        
        # Skip excluded paths
        if any(request.path.startswith(p) for p in self.EXCLUDED_PATHS):
            request._should_log = False
            return None
        
        request._should_log = True
        
        # Log request
        if settings.DEBUG or getattr(settings, 'LOG_REQUESTS', False):
            self._log_request(request)
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing response."""
        if not getattr(request, '_should_log', False):
            return response
        
        # Calculate duration
        duration = time.time() - getattr(request, '_start_time', time.time())
        duration_ms = int(duration * 1000)
        
        # Add request ID to response
        response['X-Request-ID'] = getattr(request, 'request_id', 'unknown')
        response['X-Response-Time'] = f"{duration_ms}ms"
        
        # Log response
        if settings.DEBUG or getattr(settings, 'LOG_REQUESTS', False):
            self._log_response(request, response, duration_ms)
        
        return response
    
    def _log_request(self, request):
        """Log request details."""
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        
        log_data = {
            'request_id': request.request_id,
            'method': request.method,
            'path': request.path,
            'user_id': user_id,
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100],
        }
        
        # Add query params
        if request.GET:
            log_data['query_params'] = self._mask_sensitive(dict(request.GET))
        
        # Add body for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            body = self._get_request_body(request)
            if body:
                log_data['body'] = body
        
        logger.info(
            f"[{request.request_id}] {request.method} {request.path}",
            extra={'data': log_data}
        )
    
    def _log_response(self, request, response, duration_ms):
        """Log response details."""
        log_data = {
            'request_id': request.request_id,
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': duration_ms,
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
            # Add response body for errors
            log_data['response_body'] = self._get_response_body(response)
        elif response.status_code >= 400:
            log_level = logging.WARNING
            log_data['response_body'] = self._get_response_body(response)
        else:
            log_level = logging.INFO
        
        logger.log(
            log_level,
            f"[{request.request_id}] {response.status_code} {request.method} {request.path} ({duration_ms}ms)",
            extra={'data': log_data}
        )
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_request_body(self, request):
        """Get request body, masking sensitive data."""
        try:
            if hasattr(request, 'body') and request.body:
                body = request.body[:self.MAX_BODY_SIZE]
                try:
                    body_json = json.loads(body)
                    return self._mask_sensitive(body_json)
                except json.JSONDecodeError:
                    return '<non-json body>'
        except:
            pass
        return None
    
    def _get_response_body(self, response):
        """Get response body for error logging."""
        try:
            if hasattr(response, 'content'):
                content = response.content[:self.MAX_BODY_SIZE]
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content.decode('utf-8', errors='replace')
        except:
            pass
        return None
    
    def _mask_sensitive(self, data):
        """Mask sensitive fields in data."""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if any(s in key.lower() for s in self.SENSITIVE_FIELDS):
                    masked[key] = '***MASKED***'
                elif isinstance(value, (dict, list)):
                    masked[key] = self._mask_sensitive(value)
                else:
                    masked[key] = value
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive(item) for item in data]
        return data


class SlowRequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to specifically log slow requests.
    """
    
    # Threshold for slow requests (milliseconds)
    SLOW_THRESHOLD_MS = 1000
    
    def process_request(self, request):
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        duration = time.time() - getattr(request, '_start_time', time.time())
        duration_ms = int(duration * 1000)
        
        if duration_ms >= self.SLOW_THRESHOLD_MS:
            logger.warning(
                f"Slow request detected: {request.method} {request.path} took {duration_ms}ms",
                extra={
                    'data': {
                        'method': request.method,
                        'path': request.path,
                        'duration_ms': duration_ms,
                        'status': response.status_code,
                        'user_id': request.user.id if request.user.is_authenticated else None,
                    }
                }
            )
        
        return response
