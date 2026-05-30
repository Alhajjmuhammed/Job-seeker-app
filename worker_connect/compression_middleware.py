"""
Compression middleware for API responses.
"""

import gzip
import io
from django.utils.deprecation import MiddlewareMixin


class GZipAPIMiddleware(MiddlewareMixin):
    """
    Middleware to compress API responses using gzip.
    
    Only compresses JSON responses larger than the minimum size threshold.
    """
    
    MIN_SIZE = 500  # Minimum response size to compress (bytes)
    COMPRESSIBLE_TYPES = [
        'application/json',
        'text/html',
        'text/plain',
        'text/xml',
        'application/xml',
    ]
    
    def process_response(self, request, response):
        # Skip if not an API request
        if not request.path.startswith('/api/'):
            return response
        
        # Skip if client doesn't accept gzip
        if 'gzip' not in request.META.get('HTTP_ACCEPT_ENCODING', ''):
            return response
        
        # Skip if already compressed
        if response.has_header('Content-Encoding'):
            return response
        
        # Skip if response is streaming
        if response.streaming:
            return response
        
        # Check content type
        content_type = response.get('Content-Type', '').split(';')[0]
        if content_type not in self.COMPRESSIBLE_TYPES:
            return response
        
        # Get content
        content = response.content
        
        # Skip if too small
        if len(content) < self.MIN_SIZE:
            return response
        
        # Compress content
        compressed = self._compress(content)
        
        # Only use compressed if it's actually smaller
        if len(compressed) >= len(content):
            return response
        
        # Update response
        response.content = compressed
        response['Content-Encoding'] = 'gzip'
        response['Content-Length'] = len(compressed)
        
        # Add Vary header
        if response.has_header('Vary'):
            vary = response['Vary']
            if 'Accept-Encoding' not in vary:
                response['Vary'] = f"{vary}, Accept-Encoding"
        else:
            response['Vary'] = 'Accept-Encoding'
        
        return response
    
    def _compress(self, content):
        """Compress content using gzip."""
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6) as f:
            f.write(content)
        return buffer.getvalue()


class BrotliAPIMiddleware(MiddlewareMixin):
    """
    Middleware to compress API responses using Brotli (if available).
    
    Falls back to GZip if Brotli is not available.
    """
    
    MIN_SIZE = 500
    COMPRESSIBLE_TYPES = [
        'application/json',
        'text/html',
        'text/plain',
    ]
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        try:
            import brotli
            self.brotli_available = True
        except ImportError:
            self.brotli_available = False
    
    def process_response(self, request, response):
        if not request.path.startswith('/api/'):
            return response
        
        # Check if Brotli is preferred
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        if 'br' not in accept_encoding or not self.brotli_available:
            return response
        
        if response.has_header('Content-Encoding'):
            return response
        
        if response.streaming:
            return response
        
        content_type = response.get('Content-Type', '').split(';')[0]
        if content_type not in self.COMPRESSIBLE_TYPES:
            return response
        
        content = response.content
        if len(content) < self.MIN_SIZE:
            return response
        
        # Compress with Brotli
        import brotli
        compressed = brotli.compress(content, quality=4)
        
        if len(compressed) >= len(content):
            return response
        
        response.content = compressed
        response['Content-Encoding'] = 'br'
        response['Content-Length'] = len(compressed)
        
        if response.has_header('Vary'):
            vary = response['Vary']
            if 'Accept-Encoding' not in vary:
                response['Vary'] = f"{vary}, Accept-Encoding"
        else:
            response['Vary'] = 'Accept-Encoding'
        
        return response
