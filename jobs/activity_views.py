"""
Activity feed API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .activity import Activity, ActivityService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_feed(request):
    """
    Get activity feed for the current user.
    
    Query params:
        - limit: Number of activities (default: 50)
        - types: Comma-separated activity types to filter
        - unread: Only show unread activities
    """
    limit = int(request.query_params.get('limit', 50))
    types = request.query_params.get('types')
    unread_only = request.query_params.get('unread', '').lower() == 'true'
    
    activity_types = types.split(',') if types else None
    
    activities = ActivityService.get_user_feed(
        user=request.user,
        limit=limit,
        activity_types=activity_types,
        unread_only=unread_only,
    )
    
    feed_data = []
    for activity in activities:
        feed_data.append({
            'id': activity.id,
            'type': activity.activity_type,
            'title': activity.title,
            'description': activity.description,
            'metadata': activity.metadata,
            'is_read': activity.is_read,
            'is_public': activity.is_public,
            'created_at': activity.created_at.isoformat(),
            'related_object_type': activity.content_type.model if activity.content_type else None,
            'related_object_id': activity.object_id,
        })
    
    return Response({
        'activities': feed_data,
        'count': len(feed_data),
        'unread_count': ActivityService.get_unread_count(request.user),
    })


@api_view(['GET'])
def get_public_feed(request):
    """
    Get public activity feed.
    """
    limit = int(request.query_params.get('limit', 20))
    types = request.query_params.get('types')
    
    activity_types = types.split(',') if types else None
    
    activities = ActivityService.get_public_feed(
        limit=limit,
        activity_types=activity_types,
    )
    
    feed_data = []
    for activity in activities:
        feed_data.append({
            'id': activity.id,
            'type': activity.activity_type,
            'title': activity.title,
            'description': activity.description,
            'user_name': activity.user.get_full_name() or activity.user.username,
            'created_at': activity.created_at.isoformat(),
        })
    
    return Response({
        'activities': feed_data,
        'count': len(feed_data),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_read(request, activity_id):
    """
    Mark an activity as read.
    """
    updated = ActivityService.mark_as_read(activity_id, request.user)
    
    if not updated:
        return Response({
            'error': 'Activity not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'message': 'Activity marked as read'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """
    Mark all activities as read.
    """
    types = request.data.get('types')
    activity_types = types.split(',') if types else None
    
    count = ActivityService.mark_all_as_read(
        user=request.user,
        activity_types=activity_types,
    )
    
    return Response({
        'message': f'Marked {count} activities as read'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """
    Get count of unread activities.
    """
    count = ActivityService.get_unread_count(request.user)
    
    return Response({
        'unread_count': count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_activity_types(request):
    """
    Get available activity types.
    """
    return Response({
        'activity_types': [
            {'value': code, 'label': label}
            for code, label in Activity.ACTIVITY_TYPES
        ]
    })
