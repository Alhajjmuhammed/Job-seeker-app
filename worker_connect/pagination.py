"""
Advanced pagination implementations for Worker Connect API.

Provides cursor-based pagination for better performance on large datasets.
"""

from rest_framework.pagination import (
    PageNumberPagination,
    CursorPagination,
    LimitOffsetPagination,
)
from rest_framework.response import Response
from collections import OrderedDict
import base64


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for API results."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.page.paginator.per_page),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
        ]))
    
    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'description': 'Total number of items',
                },
                'total_pages': {
                    'type': 'integer',
                    'description': 'Total number of pages',
                },
                'current_page': {
                    'type': 'integer',
                    'description': 'Current page number',
                },
                'page_size': {
                    'type': 'integer',
                    'description': 'Number of items per page',
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'description': 'URL to next page',
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'description': 'URL to previous page',
                },
                'results': schema,
            },
        }


def paginate_queryset(request, queryset, serializer_class, context=None):
    """
    Helper function to paginate a queryset in function-based views.
    
    Args:
        request: DRF request object
        queryset: Django queryset to paginate
        serializer_class: Serializer class to use
        context: Optional context dict for serializer
    
    Returns:
        Response: Paginated response with results
    """
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if context is None:
        context = {'request': request}
    else:
        context['request'] = request
    
    if page is not None:
        serializer = serializer_class(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = serializer_class(queryset, many=True, context=context)
    return Response(serializer.data)


class CursorBasedPagination(CursorPagination):
    """
    Cursor-based pagination for better performance on large datasets.
    
    Benefits:
    - Consistent results even when new items are added
    - Better performance on large datasets (no OFFSET)
    - No page number jumping (prevents accessing arbitrary pages)
    """
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-created_at'
    cursor_query_param = 'cursor'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page_size),
            ('results', data),
        ]))


class JobCursorPagination(CursorBasedPagination):
    """Cursor pagination for job listings."""
    ordering = '-created_at'


class ApplicationCursorPagination(CursorBasedPagination):
    """Cursor pagination for job applications."""
    ordering = '-created_at'


class WorkerCursorPagination(CursorBasedPagination):
    """Cursor pagination for worker listings."""
    ordering = '-rating'


class ReviewCursorPagination(CursorBasedPagination):
    """Cursor pagination for reviews."""
    ordering = '-created_at'


class ActivityCursorPagination(CursorBasedPagination):
    """Cursor pagination for activity feed."""
    page_size = 50
    ordering = '-timestamp'


class InvoiceCursorPagination(CursorBasedPagination):
    """Cursor pagination for invoices."""
    ordering = '-issue_date'


class FlexibleLimitOffsetPagination(LimitOffsetPagination):
    """
    Limit/Offset pagination with sensible defaults.
    """
    
    default_limit = 20
    max_limit = 100
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.count),
            ('limit', self.limit),
            ('offset', self.offset),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
        ]))


class KeysetPagination:
    """
    Manual keyset pagination for complex queries.
    
    Usage:
        paginator = KeysetPagination(page_size=20)
        page = paginator.paginate_queryset(queryset, request, key_field='id')
        return paginator.get_paginated_response(serializer.data)
    """
    
    def __init__(self, page_size=20, max_page_size=100):
        self.page_size = page_size
        self.max_page_size = max_page_size
        self.request = None
        self._has_next = False
        self.next_key = None
        self.prev_key = None
    
    def paginate_queryset(self, queryset, request, key_field='id', direction='desc'):
        """
        Paginate a queryset using keyset pagination.
        
        Args:
            queryset: The queryset to paginate
            request: The HTTP request
            key_field: The field to use as the pagination key
            direction: 'asc' or 'desc'
        
        Returns:
            List of items for the current page
        """
        self.request = request
        
        # Get page size from request
        page_size = int(request.query_params.get('page_size', self.page_size))
        page_size = min(page_size, self.max_page_size)
        
        # Get cursor from request
        after_key = request.query_params.get('after')
        before_key = request.query_params.get('before')
        
        # Build ordering
        order_prefix = '-' if direction == 'desc' else ''
        queryset = queryset.order_by(f'{order_prefix}{key_field}')
        
        # Apply cursor filter
        if after_key:
            decoded_key = self._decode_cursor(after_key)
            if direction == 'desc':
                queryset = queryset.filter(**{f'{key_field}__lt': decoded_key})
            else:
                queryset = queryset.filter(**{f'{key_field}__gt': decoded_key})
        elif before_key:
            decoded_key = self._decode_cursor(before_key)
            if direction == 'desc':
                queryset = queryset.filter(**{f'{key_field}__gt': decoded_key})
            else:
                queryset = queryset.filter(**{f'{key_field}__lt': decoded_key})
            # Reverse for before cursor
            queryset = queryset.reverse()
        
        # Fetch one extra to check if there's a next page
        items = list(queryset[:page_size + 1])
        
        # Check if there's a next page
        if len(items) > page_size:
            self._has_next = True
            items = items[:page_size]
        else:
            self._has_next = False
        
        # Reverse if we used before cursor
        if before_key:
            items = list(reversed(items))
        
        # Set cursor keys
        if items:
            self.next_key = self._encode_cursor(getattr(items[-1], key_field))
            self.prev_key = self._encode_cursor(getattr(items[0], key_field))
        
        return items
    
    def get_paginated_response(self, data):
        """Return paginated response."""
        response_data = OrderedDict([
            ('page_size', self.page_size),
            ('has_next', self._has_next),
            ('results', data),
        ])
        
        if self.next_key and self._has_next:
            response_data['next_cursor'] = self.next_key
        
        if self.prev_key:
            response_data['prev_cursor'] = self.prev_key
        
        return Response(response_data)
    
    def _encode_cursor(self, value):
        """Encode a cursor value."""
        return base64.urlsafe_b64encode(str(value).encode()).decode()
    
    def _decode_cursor(self, cursor):
        """Decode a cursor value."""
        try:
            return base64.urlsafe_b64decode(cursor.encode()).decode()
        except Exception:
            return None


class InfiniteScrollPagination(CursorBasedPagination):
    """
    Pagination optimized for infinite scroll in mobile apps.
    
    Features:
    - No count query (faster)
    - Simple next/previous detection
    - Optimized for append-only loading
    """
    
    page_size = 20
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('next', self.get_next_link()),
            ('has_more', self.has_next),
            ('results', data),
        ]))
    
    @property
    def has_next(self):
        """Check if there's a next page."""
        return bool(self.get_next_link())


# Pagination class mapping for easy selection
PAGINATION_CLASSES = {
    'page': StandardResultsSetPagination,
    'cursor': CursorBasedPagination,
    'limit_offset': FlexibleLimitOffsetPagination,
    'infinite': InfiniteScrollPagination,
}


def get_pagination_class(pagination_type='page'):
    """
    Get a pagination class by type.
    
    Args:
        pagination_type: One of 'page', 'cursor', 'limit_offset', 'infinite'
    
    Returns:
        Pagination class
    """
    return PAGINATION_CLASSES.get(pagination_type, StandardResultsSetPagination)
