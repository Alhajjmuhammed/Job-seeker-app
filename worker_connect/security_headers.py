"""
Security headers middleware for Worker Connect.

Adds important security headers to all responses.
"""

from django.conf import settings
from django.http import HttpResponse
import logging

logger = logging.getLogger('security')


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - Content-Security-Policy (CSP)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Strict-Transport-Security (HSTS) - production only
    - Cache-Control for sensitive endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuration
        self.debug = getattr(settings, 'DEBUG', False)
        self.hsts_enabled = getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0
        
        # CSP configuration
        self.csp_enabled = getattr(settings, 'CSP_ENABLED', True)
        self.csp_report_only = getattr(settings, 'CSP_REPORT_ONLY', self.debug)
        self.csp_report_uri = getattr(settings, 'CSP_REPORT_URI', None)
        
        # Build CSP policy
        self.csp_policy = self._build_csp_policy()
    
    def _build_csp_policy(self) -> str:
        """Build Content-Security-Policy header value."""
        # Base CSP directives
        directives = {
            'default-src': ["'self'"],
            'script-src': ["'self'"],
            'style-src': ["'self'", "'unsafe-inline'"],  # Needed for inline styles
            'img-src': ["'self'", 'data:', 'https:'],
            'font-src': ["'self'", 'https://fonts.gstatic.com'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'object-src': ["'none'"],
        }
        
        # Allow API connections in development
        if self.debug:
            directives['connect-src'].extend([
                'http://localhost:*',
                'ws://localhost:*',
            ])
            directives['script-src'].append("'unsafe-eval'")  # For React dev tools
        
        # Add report URI if configured
        if self.csp_report_uri:
            directives['report-uri'] = [self.csp_report_uri]
        
        # Allow customization from settings
        custom_csp = getattr(settings, 'CSP_DIRECTIVES', {})
        for directive, values in custom_csp.items():
            if directive in directives:
                directives[directive].extend(values)
            else:
                directives[directive] = values
        
        # Build policy string
        policy_parts = []
        for directive, values in directives.items():
            policy_parts.append(f"{directive} {' '.join(values)}")
        
        return '; '.join(policy_parts)
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Skip for static files and media
        if self._should_skip(request):
            return response
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _should_skip(self, request) -> bool:
        """Check if we should skip adding headers."""
        path = request.path
        
        # Skip for static and media files
        if path.startswith(('/static/', '/media/')):
            return True
        
        # Skip for health check endpoints
        if path.startswith('/api/health'):
            return True
        
        return False
    
    def _add_security_headers(self, response: HttpResponse, request) -> None:
        """Add security headers to response."""
        
        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options
        # Prevents clickjacking by disallowing framing
        response['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        # Legacy header for older browsers
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        # Controls referrer information sent with requests
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy (formerly Feature-Policy)
        # Controls browser features
        response['Permissions-Policy'] = (
            'accelerometer=(), '
            'camera=(), '
            'geolocation=(self), '  # Allow geolocation for job location
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'payment=(), '
            'usb=()'
        )
        
        # Content-Security-Policy
        if self.csp_enabled:
            header_name = (
                'Content-Security-Policy-Report-Only'
                if self.csp_report_only
                else 'Content-Security-Policy'
            )
            response[header_name] = self.csp_policy
        
        # Strict-Transport-Security (HSTS)
        # Only in production with HTTPS
        if not self.debug and self.hsts_enabled:
            hsts_seconds = getattr(settings, 'SECURE_HSTS_SECONDS', 31536000)
            include_subdomains = getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
            preload = getattr(settings, 'SECURE_HSTS_PRELOAD', False)
            
            hsts_value = f'max-age={hsts_seconds}'
            if include_subdomains:
                hsts_value += '; includeSubDomains'
            if preload:
                hsts_value += '; preload'
            
            response['Strict-Transport-Security'] = hsts_value
        
        # Cache-Control for sensitive endpoints
        if self._is_sensitive_endpoint(request):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Cross-Origin headers for API
        if request.path.startswith('/api/'):
            response['Cross-Origin-Resource-Policy'] = 'cross-origin'


    def _is_sensitive_endpoint(self, request) -> bool:
        """Check if endpoint handles sensitive data."""
        sensitive_paths = [
            '/api/auth/',
            '/api/accounts/',
            '/api/v1/auth/',
            '/admin/',
        ]
        
        return any(request.path.startswith(p) for p in sensitive_paths)


class APISecurityHeadersMiddleware:
    """
    Additional security headers specifically for API responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only for API endpoints
        if not request.path.startswith('/api/'):
            return response
        
        # Add API-specific headers
        response['X-API-Version'] = getattr(settings, 'API_VERSION', '1.0')
        
        # Add request ID for tracing
        request_id = getattr(request, 'request_id', None)
        if request_id:
            response['X-Request-ID'] = request_id
        
        # Add deprecation warning if applicable
        deprecation = getattr(request, 'api_deprecation', None)
        if deprecation:
            response['Deprecation'] = deprecation.get('date', 'true')
            if 'sunset' in deprecation:
                response['Sunset'] = deprecation['sunset']
            if 'link' in deprecation:
                response['Link'] = f'<{deprecation["link"]}>; rel="deprecation"'
        
        return response


class RequestIDMiddleware:
    """
    Add unique request ID to each request for tracing.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        import uuid
        
        # Get request ID from header or generate new one
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        
        request.request_id = request_id
        
        response = self.get_response(request)
        
        # Echo back request ID
        response['X-Request-ID'] = request_id
        
        return response
