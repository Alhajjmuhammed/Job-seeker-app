"""
Privacy settings API views.
Combines notification preferences with profile visibility settings.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .notification_preferences import NotificationPreferencesService
from .models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_privacy_settings(request):
    """
    Get privacy settings for the authenticated user.
    Combines notification preferences with profile visibility settings.
    """
    user = request.user
    prefs = NotificationPreferencesService.get_or_create_preferences(user)
    
    # Get user profile settings
    profile = user.worker_profile if hasattr(user, 'worker_profile') else None
    
    return Response({
        'user_id': user.id,
        'email_notifications': prefs.email_messages or prefs.email_new_jobs,
        'sms_notifications': prefs.sms_job_applications or prefs.sms_urgent_messages,
        'push_notifications': prefs.push_messages or prefs.push_new_jobs,
        'marketing_emails': prefs.email_marketing,
        'profile_visibility': 'public' if (profile and profile.is_public if profile else True) else 'private',
        'show_email': user.show_email if hasattr(user, 'show_email') else False,
        'show_phone': user.show_phone if hasattr(user, 'show_phone') else False,
        'allow_search_indexing': user.allow_search_indexing if hasattr(user, 'allow_search_indexing') else True,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_privacy_settings(request):
    """
    Update privacy settings.
    
    Request body:
        {
            "email_notifications": true,
            "sms_notifications": false,
            "push_notifications": true,
            "marketing_emails": false,
            "profile_visibility": "public",
            "show_email": false,
            "show_phone": false,
            "allow_search_indexing": true
        }
    """
    user = request.user
    data = request.data
    prefs = NotificationPreferencesService.get_or_create_preferences(user)
    
    # Update notification preferences
    if 'email_notifications' in data:
        value = data['email_notifications']
        prefs.email_messages = value
        prefs.email_new_jobs = value
        prefs.email_job_applications = value
        prefs.email_job_updates = value
    
    if 'sms_notifications' in data:
        value = data['sms_notifications']
        prefs.sms_job_applications = value
        prefs.sms_urgent_messages = value
    
    if 'push_notifications' in data:
        value = data['push_notifications']
        prefs.push_messages = value
        prefs.push_new_jobs = value
        prefs.push_job_applications = value
        prefs.push_job_updates = value
        prefs.push_reminders = value
    
    if 'marketing_emails' in data:
        prefs.email_marketing = data['marketing_emails']
    
    prefs.save()
    
    # Update profile visibility (if worker)
    if hasattr(user, 'worker_profile') and user.worker_profile:
        profile = user.worker_profile
        if 'profile_visibility' in data:
            profile.is_public = data['profile_visibility'] == 'public'
            profile.save()
    
    # Update user profile fields (add these fields to User model if needed)
    user_updated = False
    if 'show_email' in data:
        if hasattr(user, 'show_email'):
            user.show_email = data['show_email']
            user_updated = True
    
    if 'show_phone' in data:
        if hasattr(user, 'show_phone'):
            user.show_phone = data['show_phone']
            user_updated = True
    
    if 'allow_search_indexing' in data:
        if hasattr(user, 'allow_search_indexing'):
            user.allow_search_indexing = data['allow_search_indexing']
            user_updated = True
    
    if user_updated:
        user.save()
    
    return Response({
        'message': 'Privacy settings updated successfully',
        'settings': get_privacy_settings(request).data
    })
