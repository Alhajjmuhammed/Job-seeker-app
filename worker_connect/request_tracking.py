"""
Request ID tracking middleware for Worker Connect.

Adds a unique request ID to each request for tracing and debugging.
The request ID is:
- Generated automatically for each request
- Passed through from X-Request-ID header if provided
- Added to response headers
- Available in request object for logging
"""

import uuid
import logging
import threading
from django.utils.deprecation import MiddlewareMixin


# Thread-local storage for request ID
_request_id_ctx = threading.local()


def get_request_id():
    """Get the current request ID from thread-local storage."""
    return getattr(_request_id_ctx, 'request_id', None)


def set_request_id(request_id):
    """Set the request ID in thread-local storage."""
    _request_id_ctx.request_id = request_id


def clear_request_id():
    """Clear the request ID from thread-local storage."""
    _request_id_ctx.request_id = None


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware to add request ID tracking to all requests.
    
    The request ID is:
    - Extracted from X-Request-ID header if present
    - Generated as UUID4 if not provided
    - Added to response as X-Request-ID header
    - Stored in request object as request.request_id
    - Available via get_request_id() function
    """
    
    HEADER_NAME = 'X-Request-ID'
    
    def process_request(self, request):
        """Process incoming request and assign request ID."""
        # Check for existing request ID in header
        request_id = request.META.get(f'HTTP_{self.HEADER_NAME.upper().replace("-", "_")}')
        
        # Generate new request ID if not provided or invalid
        if not request_id or not self._is_valid_uuid(request_id):
            request_id = str(uuid.uuid4())
        
        # Store in request object
        request.request_id = request_id
        
        # Store in thread-local for logging
        set_request_id(request_id)
        
        return None
    
    def process_response(self, request, response):
        """Add request ID to response headers."""
        request_id = getattr(request, 'request_id', None)
        
        if request_id:
            response[self.HEADER_NAME] = request_id
        
        # Clear thread-local storage
        clear_request_id()
        
        return response
    
    def _is_valid_uuid(self, value):
        """Check if value is a valid UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError):
            return False


class RequestIDFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.
    
    Usage in logging configuration:
        'filters': {
            'request_id': {
                '()': 'worker_connect.request_tracking.RequestIDFilter',
            },
        },
        'formatters': {
            'verbose': {
                'format': '%(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s',
            },
        },
    """
    
    def filter(self, record):
        """Add request_id to log record."""
        record.request_id = get_request_id() or 'no-request-id'
        return True


class RequestIDLogAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes request ID.
    
    Usage:
        from worker_connect.request_tracking import get_logger
        logger = get_logger(__name__)
        logger.info("Processing request")  # Will include request ID
    """
    
    def process(self, msg, kwargs):
        """Process log message to include request ID."""
        request_id = get_request_id()
        if request_id:
            return f'[{request_id}] {msg}', kwargs
        return msg, kwargs


def get_logger(name):
    """
    Get a logger with request ID tracking.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        RequestIDLogAdapter: Logger adapter with request ID tracking
    """
    logger = logging.getLogger(name)
    return RequestIDLogAdapter(logger, {})
