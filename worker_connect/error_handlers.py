"""
Custom error views and decorators for the application.
Provides JSON responses for API errors, HTML for web errors, and consistent error handling decorators.
"""
import logging
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError

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


def api_error_handler(func):
    """
    Decorator for Django REST Framework views to handle errors consistently.
    Catches common exceptions and returns standardized JSON error responses.
    
    Usage:
        @api_error_handler
        @api_view(['POST'])
        def my_view(request):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        
        except ValidationError as e:
            # DRF ValidationError
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Validation error',
                    'details': e.detail if hasattr(e, 'detail') else str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except DjangoValidationError as e:
            # Django core ValidationError
            logger.warning(f"Django validation error in {func.__name__}: {str(e)}")
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Validation error',
                    'details': e.messages if hasattr(e, 'messages') else str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except PermissionDenied as e:
            logger.warning(f"Permission denied in {func.__name__}: {str(e)}")
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Permission denied',
                    'details': str(e) if str(e) else 'You do not have permission to perform this action'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        except (ObjectDoesNotExist, NotFound) as e:
            logger.warning(f"Resource not found in {func.__name__}: {str(e)}")
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Not found',
                    'details': str(e) if str(e) else 'The requested resource was not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Internal server error',
                    'details': 'An unexpected error occurred. Please try again later.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper

