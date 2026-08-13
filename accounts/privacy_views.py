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
from worker_connect.notification_models import NotificationPreference


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
        'profile_visibility': 'public' if getattr(profile, 'is_public', True) else 'private',
        'show_email': user.show_email,
        'show_phone': user.show_phone,
        'allow_search_indexing': user.allow_search_indexing,
        'analytics': user.consent_analytics,
        'personalization': user.consent_personalization,
        'third_party_sharing': user.consent_third_party_sharing,
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

    # The actual send-path (worker_connect.notification_service) checks
    # worker_connect.NotificationPreference, not this accounts model - keep
    # them in sync so toggling this settings screen actually changes what
    # gets emailed instead of only updating a preferences row nothing reads.
    wc_prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    if 'email_notifications' in data:
        value = data['email_notifications']
        wc_prefs.email_job_assignments = value
        wc_prefs.email_job_applications = value
        wc_prefs.email_messages = value
        wc_prefs.email_payments = value
        wc_prefs.email_reviews = value
    if 'marketing_emails' in data:
        wc_prefs.email_promotions = data['marketing_emails']
    wc_prefs.save()

    # Update profile visibility (if worker)
    if hasattr(user, 'worker_profile') and user.worker_profile:
        profile = user.worker_profile
        if 'profile_visibility' in data:
            profile.is_public = data['profile_visibility'] == 'public'
            profile.save(update_fields=['is_public'])

    # Update user-level privacy/consent fields
    user_fields = ['show_email', 'show_phone', 'allow_search_indexing']
    consent_field_map = {
        'analytics': 'consent_analytics',
        'personalization': 'consent_personalization',
        'third_party_sharing': 'consent_third_party_sharing',
    }
    updated_fields = []
    for field in user_fields:
        if field in data:
            setattr(user, field, bool(data[field]))
            updated_fields.append(field)
    for key, field in consent_field_map.items():
        if key in data:
            setattr(user, field, bool(data[key]))
            updated_fields.append(field)

    if updated_fields:
        user.save(update_fields=updated_fields)

    # Re-fetch updated prefs to return current state
    prefs.refresh_from_db()
    profile = user.worker_profile if hasattr(user, 'worker_profile') else None

    return Response({
        'message': 'Privacy settings updated successfully',
        'settings': {
            'user_id': user.id,
            'email_notifications': prefs.email_messages or prefs.email_new_jobs,
            'sms_notifications': prefs.sms_job_applications or prefs.sms_urgent_messages,
            'push_notifications': prefs.push_messages or prefs.push_new_jobs,
            'marketing_emails': prefs.email_marketing,
            'profile_visibility': 'public' if getattr(profile, 'is_public', True) else 'private',
            'show_email': user.show_email,
            'show_phone': user.show_phone,
            'allow_search_indexing': user.allow_search_indexing,
            'analytics': user.consent_analytics,
            'personalization': user.consent_personalization,
            'third_party_sharing': user.consent_third_party_sharing,
        }
    })
