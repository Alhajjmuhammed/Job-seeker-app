"""
Job categories management for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count

from workers.models import Category


@api_view(['GET'])
def list_categories(request):
    """
    List all job categories.
    
    Query params:
        - with_counts: Include job counts (default: false)
        - parent_only: Only show parent categories (default: false)
    """
    with_counts = request.query_params.get('with_counts', '').lower() == 'true'
    parent_only = request.query_params.get('parent_only', '').lower() == 'true'
    
    queryset = Category.objects.all()
    
    if parent_only:
        queryset = queryset.filter(parent__isnull=True)
    
    if with_counts:
        queryset = queryset.annotate(job_count=Count('jobs'))
    
    categories = []
    for cat in queryset:
        cat_data = {
            'id': cat.id,
            'name': cat.name,
            'slug': getattr(cat, 'slug', cat.name.lower().replace(' ', '-')),
            'description': getattr(cat, 'description', ''),
            'icon': getattr(cat, 'icon', ''),
            'parent_id': cat.parent_id if hasattr(cat, 'parent') else None,
        }
        
        if with_counts:
            cat_data['job_count'] = cat.job_count
        
        # Get subcategories
        if hasattr(cat, 'subcategories'):
            cat_data['subcategories'] = [
                {
                    'id': sub.id,
                    'name': sub.name,
                    'slug': getattr(sub, 'slug', sub.name.lower().replace(' ', '-')),
                }
                for sub in cat.subcategories.all()
            ]
        
        categories.append(cat_data)
    
    return Response({
        'count': len(categories),
        'categories': categories,
    })


@api_view(['GET'])
def get_category(request, category_id):
    """
    Get details for a specific category.
    """
    try:
        cat = Category.objects.annotate(
            job_count=Count('jobs')
        ).get(id=category_id)
    except Category.DoesNotExist:
        return Response({
            'error': 'Category not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    cat_data = {
        'id': cat.id,
        'name': cat.name,
        'slug': getattr(cat, 'slug', cat.name.lower().replace(' ', '-')),
        'description': getattr(cat, 'description', ''),
        'icon': getattr(cat, 'icon', ''),
        'job_count': cat.job_count,
    }
    
    # Get parent
    if hasattr(cat, 'parent') and cat.parent:
        cat_data['parent'] = {
            'id': cat.parent.id,
            'name': cat.parent.name,
        }
    
    # Get subcategories
    if hasattr(cat, 'subcategories'):
        cat_data['subcategories'] = [
            {
                'id': sub.id,
                'name': sub.name,
            }
            for sub in cat.subcategories.all()
        ]
    
    return Response(cat_data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_category(request):
    """
    Create a new category (admin only).
    
    Request body:
        {
            "name": "Plumbing",
            "description": "Plumbing services",
            "icon": "wrench",
            "parent_id": null
        }
    """
    name = request.data.get('name')
    description = request.data.get('description', '')
    icon = request.data.get('icon', '')
    parent_id = request.data.get('parent_id')
    
    if not name:
        return Response({
            'error': 'name is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check for duplicate
    if Category.objects.filter(name__iexact=name).exists():
        return Response({
            'error': 'Category with this name already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    parent = None
    if parent_id:
        try:
            parent = Category.objects.get(id=parent_id)
        except Category.DoesNotExist:
            return Response({
                'error': 'Parent category not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    category = Category.objects.create(
        name=name,
        description=description if hasattr(Category, 'description') else None,
        icon=icon if hasattr(Category, 'icon') else None,
        parent=parent if hasattr(Category, 'parent') else None,
    )
    
    return Response({
        'id': category.id,
        'name': category.name,
        'message': 'Category created successfully'
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_category(request, category_id):
    """
    Update a category (admin only).
    """
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response({
            'error': 'Category not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if 'name' in request.data:
        category.name = request.data['name']
    
    if hasattr(category, 'description') and 'description' in request.data:
        category.description = request.data['description']
    
    if hasattr(category, 'icon') and 'icon' in request.data:
        category.icon = request.data['icon']
    
    category.save()
    
    return Response({
        'id': category.id,
        'name': category.name,
        'message': 'Category updated successfully'
    })


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_category(request, category_id):
    """
    Delete a category (admin only).
    """
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response({
            'error': 'Category not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if category has jobs
    job_count = category.jobs.count()
    if job_count > 0:
        return Response({
            'error': f'Cannot delete category with {job_count} jobs. Reassign jobs first.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    category.delete()
    
    return Response({
        'message': 'Category deleted successfully'
    })


@api_view(['GET'])
def popular_categories(request):
    """
    Get popular categories by job count.
    """
    limit = int(request.query_params.get('limit', 10))
    
    categories = Category.objects.annotate(
        job_count=Count('jobs')
    ).order_by('-job_count')[:limit]
    
    result = []
    for cat in categories:
        result.append({
            'id': cat.id,
            'name': cat.name,
            'job_count': cat.job_count,
            'icon': getattr(cat, 'icon', ''),
        })
    
    return Response({'categories': result})
