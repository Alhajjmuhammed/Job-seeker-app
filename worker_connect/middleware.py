"""
API Request/Response Logging Middleware
Logs all API requests and responses for monitoring and debugging.
"""
import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('api')


class APILoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses.
    Only logs requests to /api/ endpoints.
    """
    
    SENSITIVE_FIELDS = {'password', 'token', 'secret', 'api_key', 'authorization'}
    MAX_BODY_LENGTH = 1000  # Truncate request/response bodies longer than this
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
    
    def _mask_sensitive_data(self, data):
        """Mask sensitive fields in request/response data"""
        if isinstance(data, dict):
            return {
                k: '***REDACTED***' if k.lower() in self.SENSITIVE_FIELDS else self._mask_sensitive_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data
    
    def _truncate(self, text, max_length=None):
        """Truncate text if it exceeds max length"""
        max_length = max_length or self.MAX_BODY_LENGTH
        if text and len(text) > max_length:
            return text[:max_length] + '... [TRUNCATED]'
        return text
    
    def _get_request_body(self, request):
        """Safely get and parse request body"""
        try:
            if request.content_type == 'application/json' and request.body:
                body = json.loads(request.body)
                return self._mask_sensitive_data(body)
            elif request.POST:
                return self._mask_sensitive_data(dict(request.POST))
        except (json.JSONDecodeError, Exception):
            pass
        return None
    
    def _get_response_body(self, response):
        """Safely get response body"""
        try:
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                if response.get('Content-Type', '').startswith('application/json'):
                    body = json.loads(content)
                    return self._mask_sensitive_data(body)
                return self._truncate(content)
        except (json.JSONDecodeError, UnicodeDecodeError, Exception):
            pass
        return None
    
    def process_request(self, request):
        """Store request start time"""
        if request.path.startswith('/api/'):
            request._api_start_time = time.time()
    
    def process_response(self, request, response):
        """Log API request and response"""
        if not request.path.startswith('/api/'):
            return response
        
        # Calculate request duration
        duration = None
        if hasattr(request, '_api_start_time'):
            duration = round((time.time() - request._api_start_time) * 1000, 2)
        
        # Build log data
        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': duration,
            'user': str(request.user) if request.user.is_authenticated else 'anonymous',
            'ip': self._get_client_ip(request),
        }
        
        # Add query params if present
        if request.GET:
            log_data['query_params'] = dict(request.GET)
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
            # Include more details for errors
            log_data['request_body'] = self._get_request_body(request)
            log_data['response_body'] = self._get_response_body(response)
        elif response.status_code >= 400:
            log_level = logging.WARNING
            log_data['response_body'] = self._get_response_body(response)
        else:
            log_level = logging.INFO
        
        # Log the request
        logger.log(
            log_level,
            f"API {log_data['method']} {log_data['path']} - {log_data['status']} ({log_data['duration_ms']}ms)",
            extra={'api_log': log_data}
        )
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add comprehensive security headers to all responses.
    
    These headers help protect against common web vulnerabilities:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME type sniffing
    - Information disclosure
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_response(self, request, response):
        """Add security headers to response"""
        
        # Prevent MIME type sniffing
        if 'X-Content-Type-Options' not in response:
            response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection (for older browsers)
        if 'X-XSS-Protection' not in response:
            response['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent clickjacking (can be overridden by Django's X_FRAME_OPTIONS)
        if 'X-Frame-Options' not in response:
            response['X-Frame-Options'] = 'DENY'
        
        # Referrer policy - don't leak sensitive URLs
        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions policy (formerly Feature-Policy)
        # Restrict access to sensitive browser features
        if 'Permissions-Policy' not in response:
            response['Permissions-Policy'] = (
                'accelerometer=(), '
                'camera=(), '
                'geolocation=(), '
                'gyroscope=(), '
                'magnetometer=(), '
                'microphone=(), '
                'payment=(), '
                'usb=()'
            )
        
        # Content Security Policy for API responses
        # More restrictive for JSON APIs, less so for HTML
        if request.path.startswith('/api/') and 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        
        # Prevent caching of sensitive data
        if request.path.startswith('/api/auth/') or request.path.startswith('/api/client/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
        
        # Remove server identification (if present)
        if 'Server' in response:
            del response['Server']
        
        # Remove X-Powered-By if present
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        
        return response
