"""
Standardized error codes and error handling for Worker Connect API.

Provides consistent error responses across all endpoints.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled,
)
import logging

logger = logging.getLogger('api')


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    
    # Authentication errors (1000-1099)
    INVALID_CREDENTIALS = 'AUTH_1001'
    TOKEN_EXPIRED = 'AUTH_1002'
    TOKEN_INVALID = 'AUTH_1003'
    ACCOUNT_DISABLED = 'AUTH_1004'
    ACCOUNT_NOT_VERIFIED = 'AUTH_1005'
    PASSWORD_RESET_REQUIRED = 'AUTH_1006'
    SESSION_EXPIRED = 'AUTH_1007'
    
    # Authorization errors (1100-1199)
    UNAUTHORIZED = 'AUTH_1100'
    PERMISSION_DENIED = 'AUTH_1101'
    RESOURCE_NOT_OWNED = 'AUTH_1102'
    INSUFFICIENT_ROLE = 'AUTH_1103'
    
    # Validation errors (2000-2099)
    VALIDATION_ERROR = 'VAL_2001'
    INVALID_FORMAT = 'VAL_2002'
    REQUIRED_FIELD = 'VAL_2003'
    FIELD_TOO_LONG = 'VAL_2004'
    FIELD_TOO_SHORT = 'VAL_2005'
    INVALID_EMAIL = 'VAL_2006'
    INVALID_PHONE = 'VAL_2007'
    INVALID_DATE = 'VAL_2008'
    INVALID_FILE_TYPE = 'VAL_2009'
    FILE_TOO_LARGE = 'VAL_2010'
    DUPLICATE_ENTRY = 'VAL_2011'
    INVALID_PASSWORD = 'VAL_2012'
    
    # Resource errors (3000-3099)
    NOT_FOUND = 'RES_3001'
    ALREADY_EXISTS = 'RES_3002'
    RESOURCE_DELETED = 'RES_3003'
    RESOURCE_LOCKED = 'RES_3004'
    RESOURCE_EXPIRED = 'RES_3005'
    
    # Business logic errors (4000-4099)
    JOB_NOT_OPEN = 'BIZ_4001'
    JOB_ALREADY_APPLIED = 'BIZ_4002'
    APPLICATION_NOT_PENDING = 'BIZ_4003'
    CANNOT_REVIEW_YET = 'BIZ_4004'
    ALREADY_REVIEWED = 'BIZ_4005'
    INSUFFICIENT_BALANCE = 'BIZ_4006'
    WORKER_UNAVAILABLE = 'BIZ_4007'
    JOB_FULL = 'BIZ_4008'
    INVALID_STATUS_TRANSITION = 'BIZ_4009'
    CANNOT_CANCEL = 'BIZ_4010'
    INVOICE_ALREADY_PAID = 'BIZ_4011'
    
    # Rate limiting errors (5000-5099)
    RATE_LIMITED = 'RATE_5001'
    TOO_MANY_REQUESTS = 'RATE_5002'
    DAILY_LIMIT_EXCEEDED = 'RATE_5003'
    
    # Server errors (6000-6099)
    INTERNAL_ERROR = 'SRV_6001'
    SERVICE_UNAVAILABLE = 'SRV_6002'
    DATABASE_ERROR = 'SRV_6003'
    EXTERNAL_SERVICE_ERROR = 'SRV_6004'
    TIMEOUT = 'SRV_6005'
    MAINTENANCE_MODE = 'SRV_6006'


# =============================================================================
# Error Messages
# =============================================================================

ERROR_MESSAGES: Dict[str, str] = {
    # Authentication
    ErrorCode.INVALID_CREDENTIALS: 'Invalid email or password.',
    ErrorCode.TOKEN_EXPIRED: 'Your session has expired. Please log in again.',
    ErrorCode.TOKEN_INVALID: 'Invalid authentication token.',
    ErrorCode.ACCOUNT_DISABLED: 'This account has been disabled.',
    ErrorCode.ACCOUNT_NOT_VERIFIED: 'Please verify your email address to continue.',
    ErrorCode.PASSWORD_RESET_REQUIRED: 'Password reset required. Check your email.',
    ErrorCode.SESSION_EXPIRED: 'Your session has expired.',
    
    # Authorization
    ErrorCode.UNAUTHORIZED: 'Authentication required.',
    ErrorCode.PERMISSION_DENIED: 'You do not have permission to perform this action.',
    ErrorCode.RESOURCE_NOT_OWNED: 'You can only modify your own resources.',
    ErrorCode.INSUFFICIENT_ROLE: 'Your account type cannot perform this action.',
    
    # Validation
    ErrorCode.VALIDATION_ERROR: 'Invalid input data.',
    ErrorCode.INVALID_FORMAT: 'Invalid format.',
    ErrorCode.REQUIRED_FIELD: 'This field is required.',
    ErrorCode.FIELD_TOO_LONG: 'Value is too long.',
    ErrorCode.FIELD_TOO_SHORT: 'Value is too short.',
    ErrorCode.INVALID_EMAIL: 'Enter a valid email address.',
    ErrorCode.INVALID_PHONE: 'Enter a valid phone number.',
    ErrorCode.INVALID_DATE: 'Enter a valid date.',
    ErrorCode.INVALID_FILE_TYPE: 'File type not supported.',
    ErrorCode.FILE_TOO_LARGE: 'File size exceeds maximum allowed.',
    ErrorCode.DUPLICATE_ENTRY: 'This entry already exists.',
    ErrorCode.INVALID_PASSWORD: 'Password does not meet requirements.',
    
    # Resources
    ErrorCode.NOT_FOUND: 'The requested resource was not found.',
    ErrorCode.ALREADY_EXISTS: 'A resource with this identifier already exists.',
    ErrorCode.RESOURCE_DELETED: 'This resource has been deleted.',
    ErrorCode.RESOURCE_LOCKED: 'This resource is currently locked.',
    ErrorCode.RESOURCE_EXPIRED: 'This resource has expired.',
    
    # Business logic
    ErrorCode.JOB_NOT_OPEN: 'This job is no longer accepting applications.',
    ErrorCode.JOB_ALREADY_APPLIED: 'You have already applied to this job.',
    ErrorCode.APPLICATION_NOT_PENDING: 'This application cannot be modified.',
    ErrorCode.CANNOT_REVIEW_YET: 'You can only review after the job is completed.',
    ErrorCode.ALREADY_REVIEWED: 'You have already submitted a review.',
    ErrorCode.INSUFFICIENT_BALANCE: 'Insufficient balance for this operation.',
    ErrorCode.WORKER_UNAVAILABLE: 'This worker is not currently available.',
    ErrorCode.JOB_FULL: 'This job has reached the maximum number of workers.',
    ErrorCode.INVALID_STATUS_TRANSITION: 'Invalid status change.',
    ErrorCode.CANNOT_CANCEL: 'This cannot be cancelled at this stage.',
    ErrorCode.INVOICE_ALREADY_PAID: 'This invoice has already been paid.',
    
    # Rate limiting
    ErrorCode.RATE_LIMITED: 'Too many requests. Please try again later.',
    ErrorCode.TOO_MANY_REQUESTS: 'Request limit exceeded.',
    ErrorCode.DAILY_LIMIT_EXCEEDED: 'Daily limit exceeded. Try again tomorrow.',
    
    # Server
    ErrorCode.INTERNAL_ERROR: 'An unexpected error occurred.',
    ErrorCode.SERVICE_UNAVAILABLE: 'Service temporarily unavailable.',
    ErrorCode.DATABASE_ERROR: 'Database error occurred.',
    ErrorCode.EXTERNAL_SERVICE_ERROR: 'External service error.',
    ErrorCode.TIMEOUT: 'Request timed out.',
    ErrorCode.MAINTENANCE_MODE: 'System is under maintenance.',
}


# =============================================================================
# API Error Class
# =============================================================================

class APIError(APIException):
    """
    Custom API exception with standardized error format.
    
    Usage:
        raise APIError(
            code=ErrorCode.JOB_NOT_OPEN,
            message='Custom message',  # Optional
            details={'job_id': 123},  # Optional
            status_code=400  # Optional
        )
    """
    
    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message or ERROR_MESSAGES.get(code, 'An error occurred.')
        self.details = details or {}
        self.status_code = status_code
        
        super().__init__(detail=self.message)
    
    def get_full_details(self) -> Dict[str, Any]:
        """Get the full error response."""
        error = {
            'code': self.code,
            'message': self.message,
        }
        if self.details:
            error['details'] = self.details
        return {'error': error}


# =============================================================================
# Custom Exception Handler
# =============================================================================

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    
    Converts all exceptions to standardized error format.
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)
    
    # Handle our custom APIError
    if isinstance(exc, APIError):
        return Response(
            exc.get_full_details(),
            status=exc.status_code,
        )
    
    # Handle DRF validation errors
    if isinstance(exc, ValidationError):
        return Response(
            {
                'error': {
                    'code': ErrorCode.VALIDATION_ERROR.value,
                    'message': 'Invalid input data.',
                    'details': exc.detail,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                'error': {
                    'code': ErrorCode.VALIDATION_ERROR.value,
                    'message': 'Validation error.',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'error': exc.messages},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Handle authentication errors
    if isinstance(exc, AuthenticationFailed):
        return Response(
            {
                'error': {
                    'code': ErrorCode.INVALID_CREDENTIALS.value,
                    'message': str(exc.detail),
                }
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    if isinstance(exc, NotAuthenticated):
        return Response(
            {
                'error': {
                    'code': ErrorCode.UNAUTHORIZED.value,
                    'message': 'Authentication required.',
                }
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Handle permission errors
    if isinstance(exc, PermissionDenied):
        return Response(
            {
                'error': {
                    'code': ErrorCode.PERMISSION_DENIED.value,
                    'message': str(exc.detail) or 'Permission denied.',
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    
    # Handle not found errors
    if isinstance(exc, NotFound):
        return Response(
            {
                'error': {
                    'code': ErrorCode.NOT_FOUND.value,
                    'message': str(exc.detail) or 'Resource not found.',
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Handle method not allowed
    if isinstance(exc, MethodNotAllowed):
        return Response(
            {
                'error': {
                    'code': 'METHOD_NOT_ALLOWED',
                    'message': str(exc.detail),
                }
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
    
    # Handle throttling
    if isinstance(exc, Throttled):
        return Response(
            {
                'error': {
                    'code': ErrorCode.RATE_LIMITED.value,
                    'message': 'Too many requests.',
                    'details': {
                        'retry_after': exc.wait,
                    },
                }
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    # Log unexpected errors
    if response is None:
        logger.exception(f"Unhandled exception: {exc}")
        return Response(
            {
                'error': {
                    'code': ErrorCode.INTERNAL_ERROR.value,
                    'message': 'An unexpected error occurred.',
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    # Wrap other responses in standard format
    if response is not None and not isinstance(response.data, dict) or 'error' not in response.data:
        response.data = {
            'error': {
                'code': f'HTTP_{response.status_code}',
                'message': str(response.data) if not isinstance(response.data, dict) else 'Error',
                'details': response.data if isinstance(response.data, dict) else None,
            }
        }
    
    return response


# =============================================================================
# Helper Functions
# =============================================================================

def raise_validation_error(
    field: str,
    message: str,
    code: ErrorCode = ErrorCode.VALIDATION_ERROR,
) -> None:
    """Raise a validation error for a specific field."""
    raise APIError(
        code=code,
        message=message,
        details={field: [message]},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def raise_not_found(resource_type: str, identifier: Any = None) -> None:
    """Raise a not found error."""
    message = f'{resource_type} not found.'
    if identifier:
        message = f'{resource_type} with ID {identifier} not found.'
    
    raise APIError(
        code=ErrorCode.NOT_FOUND,
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
    )


def raise_permission_denied(message: str = None) -> None:
    """Raise a permission denied error."""
    raise APIError(
        code=ErrorCode.PERMISSION_DENIED,
        message=message or 'You do not have permission to perform this action.',
        status_code=status.HTTP_403_FORBIDDEN,
    )


def raise_business_error(code: ErrorCode, message: str = None, details: Dict = None) -> None:
    """Raise a business logic error."""
    raise APIError(
        code=code,
        message=message,
        details=details,
        status_code=status.HTTP_400_BAD_REQUEST,
    )
