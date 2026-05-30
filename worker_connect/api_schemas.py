"""
Enhanced OpenAPI schema definitions for Worker Connect API.

Provides detailed examples, descriptions, and custom schema classes.
"""

from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import status


# =============================================================================
# Common Response Schemas
# =============================================================================

ERROR_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'error': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='Error code'),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Human-readable error message'),
                'details': openapi.Schema(type=openapi.TYPE_OBJECT, description='Additional error details'),
            },
            required=['code', 'message'],
        ),
    },
)

PAGINATED_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of items'),
        'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of pages'),
        'current_page': openapi.Schema(type=openapi.TYPE_INTEGER, description='Current page number'),
        'page_size': openapi.Schema(type=openapi.TYPE_INTEGER, description='Items per page'),
        'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='URL to next page'),
        'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='URL to previous page'),
        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
    },
)

SUCCESS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
        'message': openapi.Schema(type=openapi.TYPE_STRING),
        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
    },
)


# =============================================================================
# Authentication Schemas
# =============================================================================

LOGIN_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['email', 'password'],
    properties={
        'email': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_EMAIL,
            description='User email address',
            example='user@example.com',
        ),
        'password': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_PASSWORD,
            description='User password (min 8 characters)',
            example='SecurePass123!',
        ),
    },
)

LOGIN_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'token': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Authentication token for API requests',
            example='9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b',
        ),
        'user': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                'email': openapi.Schema(type=openapi.TYPE_STRING, example='user@example.com'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, example='John'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, example='Doe'),
                'user_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['worker', 'client']),
            },
        ),
    },
)

REGISTER_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['email', 'password', 'first_name', 'last_name', 'user_type'],
    properties={
        'email': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_EMAIL,
            example='newuser@example.com',
        ),
        'password': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_PASSWORD,
            description='Min 8 chars, must include uppercase, lowercase, and number',
            example='SecurePass123!',
        ),
        'first_name': openapi.Schema(type=openapi.TYPE_STRING, example='Jane'),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING, example='Smith'),
        'user_type': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['worker', 'client'],
            description='Type of account to create',
        ),
        'phone': openapi.Schema(type=openapi.TYPE_STRING, example='+1234567890'),
    },
)


# =============================================================================
# Job Schemas
# =============================================================================

JOB_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, read_only=True, example=1),
        'title': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Job title',
            example='Home Cleaning Service',
        ),
        'description': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Detailed job description',
            example='Need a thorough cleaning of a 3-bedroom house including kitchen and bathrooms.',
        ),
        'category': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='Cleaning'),
            },
        ),
        'budget': openapi.Schema(
            type=openapi.TYPE_NUMBER,
            format='decimal',
            description='Budget in USD',
            example=150.00,
        ),
        'location': openapi.Schema(
            type=openapi.TYPE_STRING,
            example='123 Main St, City, State 12345',
        ),
        'status': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['open', 'in_progress', 'completed', 'cancelled'],
            example='open',
        ),
        'scheduled_date': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
            example='2025-01-15T10:00:00Z',
        ),
        'created_at': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
            read_only=True,
        ),
        'client': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='John Doe'),
                'rating': openapi.Schema(type=openapi.TYPE_NUMBER, example=4.5),
            },
        ),
    },
)

JOB_CREATE_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['title', 'description', 'category_id', 'budget'],
    properties={
        'title': openapi.Schema(type=openapi.TYPE_STRING, example='Plumbing Repair'),
        'description': openapi.Schema(
            type=openapi.TYPE_STRING,
            example='Fix leaking kitchen faucet and check bathroom pipes.',
        ),
        'category_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=2),
        'budget': openapi.Schema(type=openapi.TYPE_NUMBER, example=200.00),
        'location': openapi.Schema(type=openapi.TYPE_STRING, example='456 Oak Ave'),
        'scheduled_date': openapi.Schema(type=openapi.TYPE_STRING, example='2025-01-20T14:00:00Z'),
        'required_skills': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER),
            example=[1, 3, 5],
        ),
    },
)


# =============================================================================
# Worker Schemas
# =============================================================================

WORKER_PROFILE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        'user': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, example='Mike'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, example='Johnson'),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        'bio': openapi.Schema(
            type=openapi.TYPE_STRING,
            example='Experienced plumber with 10+ years in residential and commercial work.',
        ),
        'hourly_rate': openapi.Schema(type=openapi.TYPE_NUMBER, example=45.00),
        'rating': openapi.Schema(type=openapi.TYPE_NUMBER, example=4.8),
        'total_reviews': openapi.Schema(type=openapi.TYPE_INTEGER, example=127),
        'total_jobs_completed': openapi.Schema(type=openapi.TYPE_INTEGER, example=89),
        'is_verified': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
        'availability_status': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['available', 'busy', 'unavailable'],
            example='available',
        ),
        'categories': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
        'skills': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            example=['Pipe repair', 'Drain cleaning', 'Water heater installation'],
        ),
        'badges': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'name': openapi.Schema(type=openapi.TYPE_STRING, example='Top Rated'),
                    'icon': openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
    },
)


# =============================================================================
# Application Schemas
# =============================================================================

JOB_APPLICATION_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'job': openapi.Schema(type=openapi.TYPE_INTEGER, description='Job ID'),
        'worker': openapi.Schema(type=openapi.TYPE_OBJECT),
        'proposed_rate': openapi.Schema(type=openapi.TYPE_NUMBER, example=40.00),
        'cover_letter': openapi.Schema(
            type=openapi.TYPE_STRING,
            example='I have extensive experience in this type of work...',
        ),
        'status': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['pending', 'accepted', 'rejected', 'withdrawn'],
        ),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
    },
)

APPLICATION_CREATE_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['job_id'],
    properties={
        'job_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        'proposed_rate': openapi.Schema(
            type=openapi.TYPE_NUMBER,
            description='Your proposed hourly rate (optional)',
            example=45.00,
        ),
        'cover_letter': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Why you are a good fit for this job',
            example='I have 5 years of experience in similar projects...',
        ),
    },
)


# =============================================================================
# Review Schemas
# =============================================================================

REVIEW_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'reviewer': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        'rating': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            minimum=1,
            maximum=5,
            example=5,
        ),
        'title': openapi.Schema(type=openapi.TYPE_STRING, example='Excellent work!'),
        'comment': openapi.Schema(
            type=openapi.TYPE_STRING,
            example='Very professional and completed the job ahead of schedule.',
        ),
        'job': openapi.Schema(type=openapi.TYPE_INTEGER),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
    },
)

REVIEW_CREATE_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['rating', 'job_id'],
    properties={
        'job_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        'rating': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5, example=5),
        'title': openapi.Schema(type=openapi.TYPE_STRING, example='Great service!'),
        'comment': openapi.Schema(type=openapi.TYPE_STRING, example='Would highly recommend.'),
    },
)


# =============================================================================
# Invoice Schemas
# =============================================================================

INVOICE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'invoice_number': openapi.Schema(type=openapi.TYPE_STRING, example='INV-2025-0001'),
        'job': openapi.Schema(type=openapi.TYPE_INTEGER),
        'worker': openapi.Schema(type=openapi.TYPE_OBJECT),
        'client': openapi.Schema(type=openapi.TYPE_OBJECT),
        'subtotal': openapi.Schema(type=openapi.TYPE_NUMBER, example=200.00),
        'tax_amount': openapi.Schema(type=openapi.TYPE_NUMBER, example=20.00),
        'total': openapi.Schema(type=openapi.TYPE_NUMBER, example=220.00),
        'status': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['draft', 'sent', 'paid', 'overdue', 'cancelled'],
        ),
        'issue_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        'due_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        'items': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                    'quantity': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'unit_price': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'total': openapi.Schema(type=openapi.TYPE_NUMBER),
                },
            ),
        ),
    },
)


# =============================================================================
# Common Parameters
# =============================================================================

PAGINATION_PARAMETERS = [
    openapi.Parameter(
        'page',
        openapi.IN_QUERY,
        description='Page number',
        type=openapi.TYPE_INTEGER,
        default=1,
    ),
    openapi.Parameter(
        'page_size',
        openapi.IN_QUERY,
        description='Number of items per page (max 100)',
        type=openapi.TYPE_INTEGER,
        default=20,
    ),
]

SEARCH_PARAMETER = openapi.Parameter(
    'search',
    openapi.IN_QUERY,
    description='Search query string',
    type=openapi.TYPE_STRING,
)

ORDERING_PARAMETER = openapi.Parameter(
    'ordering',
    openapi.IN_QUERY,
    description='Field to order by (prefix with - for descending)',
    type=openapi.TYPE_STRING,
)

JOB_FILTER_PARAMETERS = [
    openapi.Parameter(
        'status',
        openapi.IN_QUERY,
        description='Filter by job status',
        type=openapi.TYPE_STRING,
        enum=['open', 'in_progress', 'completed', 'cancelled'],
    ),
    openapi.Parameter(
        'category',
        openapi.IN_QUERY,
        description='Filter by category ID',
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        'min_budget',
        openapi.IN_QUERY,
        description='Minimum budget filter',
        type=openapi.TYPE_NUMBER,
    ),
    openapi.Parameter(
        'max_budget',
        openapi.IN_QUERY,
        description='Maximum budget filter',
        type=openapi.TYPE_NUMBER,
    ),
    openapi.Parameter(
        'location',
        openapi.IN_QUERY,
        description='Filter by location (partial match)',
        type=openapi.TYPE_STRING,
    ),
]

WORKER_FILTER_PARAMETERS = [
    openapi.Parameter(
        'category',
        openapi.IN_QUERY,
        description='Filter by category ID',
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        'min_rating',
        openapi.IN_QUERY,
        description='Minimum rating filter',
        type=openapi.TYPE_NUMBER,
    ),
    openapi.Parameter(
        'max_rate',
        openapi.IN_QUERY,
        description='Maximum hourly rate',
        type=openapi.TYPE_NUMBER,
    ),
    openapi.Parameter(
        'is_verified',
        openapi.IN_QUERY,
        description='Filter verified workers only',
        type=openapi.TYPE_BOOLEAN,
    ),
    openapi.Parameter(
        'availability',
        openapi.IN_QUERY,
        description='Filter by availability status',
        type=openapi.TYPE_STRING,
        enum=['available', 'busy', 'unavailable'],
    ),
]


# =============================================================================
# Response Examples
# =============================================================================

RESPONSE_EXAMPLES = {
    'login_success': {
        'token': '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b',
        'user': {
            'id': 1,
            'email': 'user@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'user_type': 'worker',
        },
    },
    'login_error': {
        'error': {
            'code': 'INVALID_CREDENTIALS',
            'message': 'Invalid email or password',
        },
    },
    'validation_error': {
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid input data',
            'details': {
                'email': ['Enter a valid email address.'],
                'password': ['This field is required.'],
            },
        },
    },
    'not_found': {
        'error': {
            'code': 'NOT_FOUND',
            'message': 'The requested resource was not found',
        },
    },
    'unauthorized': {
        'error': {
            'code': 'UNAUTHORIZED',
            'message': 'Authentication credentials were not provided',
        },
    },
    'forbidden': {
        'error': {
            'code': 'FORBIDDEN',
            'message': 'You do not have permission to perform this action',
        },
    },
    'rate_limited': {
        'error': {
            'code': 'RATE_LIMITED',
            'message': 'Too many requests. Please try again later.',
            'details': {
                'retry_after': 60,
            },
        },
    },
}


# =============================================================================
# Custom Auto Schema
# =============================================================================

class WorkerConnectAutoSchema(SwaggerAutoSchema):
    """
    Custom auto schema that adds common responses and security requirements.
    """
    
    def get_responses(self):
        responses = super().get_responses()
        
        # Add common error responses
        if '401' not in responses:
            responses['401'] = openapi.Response(
                description='Unauthorized - Authentication required',
                schema=ERROR_RESPONSE,
            )
        
        if '403' not in responses:
            responses['403'] = openapi.Response(
                description='Forbidden - Insufficient permissions',
                schema=ERROR_RESPONSE,
            )
        
        if '429' not in responses:
            responses['429'] = openapi.Response(
                description='Too Many Requests - Rate limit exceeded',
                schema=ERROR_RESPONSE,
            )
        
        if '500' not in responses:
            responses['500'] = openapi.Response(
                description='Internal Server Error',
                schema=ERROR_RESPONSE,
            )
        
        return responses
