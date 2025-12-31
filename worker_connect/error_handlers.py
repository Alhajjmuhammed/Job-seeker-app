"""
Custom error views for the application.
Provides JSON responses for API errors and HTML for web errors.
"""
import logging
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def is_api_request(request):
    """Check if the request is for the API"""
    return (
        request.path.startswith('/api/') or
        request.content_type == 'application/json' or
        request.headers.get('Accept', '').startswith('application/json')
    )


def handler400(request, exception=None):
    """Handle 400 Bad Request errors"""
    logger.warning(f"Bad request: {request.path} - {exception}")
    
    if is_api_request(request):
        return JsonResponse({
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server.'
        }, status=400)
    
    return render(request, 'errors/400.html', status=400)


def handler403(request, exception=None):
    """Handle 403 Forbidden errors"""
    logger.warning(f"Forbidden access: {request.path} - User: {request.user}")
    
    if is_api_request(request):
        return JsonResponse({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.'
        }, status=403)
    
    return render(request, 'errors/403.html', status=403)


def handler404(request, exception=None):
    """Handle 404 Not Found errors"""
    logger.info(f"Page not found: {request.path}")
    
    if is_api_request(request):
        return JsonResponse({
            'error': 'Not Found',
            'message': 'The requested resource was not found.'
        }, status=404)
    
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Handle 500 Internal Server Error"""
    logger.error(f"Server error: {request.path}", exc_info=True)
    
    if is_api_request(request):
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later.'
        }, status=500)
    
    return render(request, 'errors/500.html', status=500)
