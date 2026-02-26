from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .notification_models import Notification, NotificationPreference, PushToken
from .notification_serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    PushTokenSerializer
)

class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Get user's notifications with pagination"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Filter by read status
    is_read = request.GET.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
    # Filter by notification type
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    paginator = NotificationPagination()
    page = paginator.paginate_queryset(notifications, request)
    
    if page is not None:
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response({
        'success': True,
        'notifications': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_counts(request):
    """Get notification counts"""
    user_notifications = Notification.objects.filter(recipient=request.user)
    
    counts = {
        'total': user_notifications.count(),
        'unread': user_notifications.filter(is_read=False).count(),
        'by_type': {}
    }
    
    # Count by type
    for notification_type, label in Notification.NOTIFICATION_TYPES:
        count = user_notifications.filter(notification_type=notification_type).count()
        unread_count = user_notifications.filter(
            notification_type=notification_type,
            is_read=False
        ).count()
        
        counts['by_type'][notification_type] = {
            'total': count,
            'unread': unread_count,
            'label': label
        }
    
    return Response({
        'success': True,
        'counts': counts
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    
    notification.mark_as_read()
    
    return Response({
        'success': True,
        'message': 'Notification marked as read'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications as read"""
    updated = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({
        'success': True,
        'message': f'Marked {updated} notifications as read'
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    
    notification.delete()
    
    return Response({
        'success': True,
        'message': 'Notification deleted'
    })

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'GET':
        serializer = NotificationPreferenceSerializer(preferences)
        return Response({
            'success': True,
            'preferences': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = NotificationPreferenceSerializer(
            preferences,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Preferences updated successfully',
                'preferences': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_push_token(request):
    """Register push notification token"""
    serializer = PushTokenSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Push token registered successfully'
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unregister_push_token(request):
    """Unregister push notification token"""
    token = request.data.get('token')
    if not token:
        return Response({
            'success': False,
            'error': 'Token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    PushToken.objects.filter(
        user=request.user,
        token=token
    ).update(is_active=False)
    
    return Response({
        'success': True,
        'message': 'Push token unregistered successfully'
    })