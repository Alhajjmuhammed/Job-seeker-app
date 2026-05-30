"""
Notification preferences API views.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .notification_preferences import NotificationPreferencesService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_preferences(request):
    """
    Get notification preferences for the authenticated user.
    """
    preferences = NotificationPreferencesService.get_preferences_dict(request.user)
    
    return Response({
        'user_id': request.user.id,
        'preferences': preferences,
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_notification_preferences(request):
    """
    Update notification preferences.
    
    Request body:
        {
            "email": {
                "new_jobs": false,
                "frequency": "daily"
            },
            "push": {
                "messages": true
            },
            "quiet_hours": {
                "enabled": true,
                "start": "22:00",
                "end": "07:00"
            }
        }
    """
    updates = request.data
    
    if not updates:
        return Response({
            'error': 'No updates provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = NotificationPreferencesService.update_preferences(
        request.user,
        updates
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mute_notifications(request):
    """
    Mute all notifications.
    
    Query params:
        - channel: Optional - 'email', 'push', or 'sms' to mute only that channel
    """
    channel = request.query_params.get('channel')
    
    if channel and channel not in ['email', 'push', 'sms']:
        return Response({
            'error': 'Invalid channel. Must be email, push, or sms'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = NotificationPreferencesService.mute_all(request.user, channel)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unmute_notifications(request):
    """
    Unmute all notifications.
    
    Query params:
        - channel: Optional - 'email', 'push', or 'sms' to unmute only that channel
    """
    channel = request.query_params.get('channel')
    
    if channel and channel not in ['email', 'push', 'sms']:
        return Response({
            'error': 'Invalid channel. Must be email, push, or sms'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = NotificationPreferencesService.unmute_all(request.user, channel)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_quiet_hours(request):
    """
    Set quiet hours for notifications.
    
    Request body:
        {
            "enabled": true,
            "start": "22:00",
            "end": "07:00"
        }
    """
    enabled = request.data.get('enabled', False)
    start = request.data.get('start')
    end = request.data.get('end')
    
    if enabled and (not start or not end):
        return Response({
            'error': 'start and end times are required when enabling quiet hours'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    updates = {
        'quiet_hours': {
            'enabled': enabled,
            'start': start,
            'end': end,
        }
    }
    
    result = NotificationPreferencesService.update_preferences(
        request.user,
        updates
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_email_frequency(request):
    """
    Set email notification frequency.
    
    Request body:
        {
            "frequency": "instant" | "hourly" | "daily" | "weekly"
        }
    """
    frequency = request.data.get('frequency')
    
    valid_frequencies = ['instant', 'hourly', 'daily', 'weekly']
    if frequency not in valid_frequencies:
        return Response({
            'error': f'Invalid frequency. Must be one of: {valid_frequencies}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    updates = {
        'email': {
            'frequency': frequency,
        }
    }
    
    result = NotificationPreferencesService.update_preferences(
        request.user,
        updates
    )
    
    return Response(result)
