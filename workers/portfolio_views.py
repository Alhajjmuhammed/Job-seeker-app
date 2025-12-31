"""
Portfolio API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from .portfolio import PortfolioItem, PortfolioService
from .models import WorkerProfile


def get_worker_from_request(request):
    """Helper to get WorkerProfile from request user."""
    try:
        return WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_portfolio(request):
    """
    Get the current worker's portfolio items.
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get all items (including private)
    items = PortfolioService.get_worker_portfolio(worker, public_only=False)
    stats = PortfolioService.get_portfolio_stats(worker)
    
    portfolio_data = []
    for item in items:
        portfolio_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'media_type': item.media_type,
            'media_url': item.media_file.url if item.media_file else None,
            'thumbnail_url': item.thumbnail.url if item.thumbnail else None,
            'external_url': item.external_url,
            'category_id': item.category_id,
            'tags': item.tags,
            'related_job_id': item.related_job_id,
            'is_featured': item.is_featured,
            'is_public': item.is_public,
            'display_order': item.display_order,
            'created_at': item.created_at.isoformat(),
        })
    
    return Response({
        'portfolio': portfolio_data,
        'stats': stats,
    })


@api_view(['GET'])
def get_worker_portfolio(request, worker_id):
    """
    Get a worker's public portfolio items.
    """
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Worker not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    category = request.query_params.get('category')
    items = PortfolioService.get_worker_portfolio(
        worker, 
        public_only=True,
        category=category
    )
    
    portfolio_data = []
    for item in items:
        portfolio_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'media_type': item.media_type,
            'media_url': item.media_file.url if item.media_file else None,
            'thumbnail_url': item.thumbnail.url if item.thumbnail else None,
            'external_url': item.external_url,
            'category_id': item.category_id,
            'tags': item.tags,
            'is_featured': item.is_featured,
            'created_at': item.created_at.isoformat(),
        })
    
    return Response({
        'worker_id': worker_id,
        'portfolio': portfolio_data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def add_portfolio_item(request):
    """
    Add a portfolio item.
    
    Request body:
        {
            "title": "Kitchen Renovation",
            "description": "Complete kitchen renovation...",
            "media_type": "image",
            "category_id": 1,
            "tags": ["renovation", "kitchen"],
            "is_public": true
        }
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    title = request.data.get('title')
    if not title:
        return Response({
            'error': 'title is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    description = request.data.get('description', '')
    media_type = request.data.get('media_type', 'image')
    media_file = request.FILES.get('media_file')
    external_url = request.data.get('external_url')
    category_id = request.data.get('category_id')
    tags = request.data.get('tags', [])
    related_job_id = request.data.get('related_job_id')
    is_public = request.data.get('is_public', True)
    
    # Get category if provided
    category = None
    if category_id:
        from .models import Category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            pass
    
    # Get related job if provided
    related_job = None
    if related_job_id:
        from jobs.models import JobRequest
        try:
            related_job = JobRequest.objects.get(id=related_job_id)
        except JobRequest.DoesNotExist:
            pass
    
    item = PortfolioService.add_portfolio_item(
        worker=worker,
        title=title,
        description=description,
        media_type=media_type,
        media_file=media_file,
        external_url=external_url,
        category=category,
        tags=tags if isinstance(tags, list) else [],
        related_job=related_job,
        is_public=is_public,
    )
    
    return Response({
        'id': item.id,
        'title': item.title,
        'message': 'Portfolio item added successfully'
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_portfolio_item(request, item_id):
    """
    Update a portfolio item.
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    update_data = {}
    
    for field in ['title', 'description', 'media_type', 'external_url', 
                  'tags', 'is_featured', 'is_public', 'display_order']:
        if field in request.data:
            update_data[field] = request.data[field]
    
    if 'media_file' in request.FILES:
        update_data['media_file'] = request.FILES['media_file']
    
    item = PortfolioService.update_portfolio_item(item_id, worker, **update_data)
    
    if not item:
        return Response({
            'error': 'Portfolio item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': item.id,
        'title': item.title,
        'message': 'Portfolio item updated successfully'
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_portfolio_item(request, item_id):
    """
    Delete a portfolio item.
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    success = PortfolioService.delete_portfolio_item(item_id, worker)
    
    if not success:
        return Response({
            'error': 'Portfolio item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'message': 'Portfolio item deleted successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reorder_portfolio(request):
    """
    Reorder portfolio items.
    
    Request body:
        {
            "item_order": [3, 1, 2, 5, 4]
        }
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    item_order = request.data.get('item_order', [])
    
    if not item_order:
        return Response({
            'error': 'item_order is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    PortfolioService.reorder_items(worker, item_order)
    
    return Response({
        'message': 'Portfolio reordered successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_featured(request, item_id):
    """
    Toggle featured status of a portfolio item.
    """
    worker = get_worker_from_request(request)
    if not worker:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    is_featured = request.data.get('is_featured', True)
    
    item = PortfolioService.set_featured(item_id, worker, is_featured)
    
    if not item:
        return Response({
            'error': 'Portfolio item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': item.id,
        'is_featured': item.is_featured,
        'message': 'Featured status updated'
    })


@api_view(['GET'])
def get_featured_portfolio(request, worker_id):
    """
    Get featured portfolio items for a worker.
    """
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Worker not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    limit = int(request.query_params.get('limit', 5))
    items = PortfolioService.get_featured_items(worker, limit)
    
    portfolio_data = []
    for item in items:
        portfolio_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'media_type': item.media_type,
            'media_url': item.media_file.url if item.media_file else None,
            'thumbnail_url': item.thumbnail.url if item.thumbnail else None,
        })
    
    return Response({
        'worker_id': worker_id,
        'featured_items': portfolio_data,
    })
