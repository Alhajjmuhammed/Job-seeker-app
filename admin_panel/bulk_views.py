"""
Admin bulk action views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.models import JobApplication
from jobs.service_request_models import ServiceRequest
from worker_connect.notification_service import NotificationService


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_user_action(request):
    """
    Perform bulk actions on users.
    
    Request body:
        {
            "user_ids": [1, 2, 3],
            "action": "activate" | "deactivate" | "delete" | "verify"
        }
    """
    user_ids = request.data.get('user_ids', [])
    action = request.data.get('action')
    
    if not user_ids:
        return Response({
            'error': 'user_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valid_actions = ['activate', 'deactivate', 'delete', 'verify']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Don't allow actions on superusers
    users = User.objects.filter(id__in=user_ids).exclude(is_superuser=True)
    
    affected_count = 0
    
    with transaction.atomic():
        if action == 'activate':
            affected_count = users.update(is_active=True)
        
        elif action == 'deactivate':
            affected_count = users.update(is_active=False)
        
        elif action == 'delete':
            affected_count = users.count()
            users.delete()
        
        elif action == 'verify':
            # Verify associated profiles
            for user in users:
                if hasattr(user, 'worker_profile'):
                    user.worker_profile.verification_status = 'verified'
                    user.worker_profile.save()
                    affected_count += 1
    
    return Response({
        'success': True,
        'action': action,
        'affected_count': affected_count,
        'message': f'{action.capitalize()} completed for {affected_count} users'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_worker_action(request):
    """
    Perform bulk actions on workers.
    
    Request body:
        {
            "worker_ids": [1, 2, 3],
            "action": "verify" | "unverify" | "feature" | "unfeature" | "suspend"
        }
    """
    worker_ids = request.data.get('worker_ids', [])
    action = request.data.get('action')
    
    if not worker_ids:
        return Response({
            'error': 'worker_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valid_actions = ['verify', 'unverify', 'feature', 'unfeature', 'suspend']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    workers = WorkerProfile.objects.filter(id__in=worker_ids)
    affected_count = 0
    
    with transaction.atomic():
        if action == 'verify':
            affected_count = workers.update(verification_status='verified')

        elif action == 'unverify':
            affected_count = workers.update(verification_status='pending')
        
        elif action == 'feature':
            affected_count = workers.update(is_featured=True)
        
        elif action == 'unfeature':
            affected_count = workers.update(is_featured=False)
        
        elif action == 'suspend':
            # Deactivate user accounts. Also flip availability away from
            # 'available' - every "who can be assigned right now" query in
            # the admin panel (admin_available_workers, admin_assign_worker,
            # admin_bulk_assign_workers, admin_auto_assign_nearest_workers)
            # filters on WorkerProfile.availability, not on the linked
            # User.is_active, so a worker suspended without this would keep
            # showing up as assignable despite the deactivated account.
            for worker in workers:
                worker.user.is_active = False
                worker.user.save()
                worker.availability = 'offline'
                worker.save()
                affected_count += 1
    
    return Response({
        'success': True,
        'action': action,
        'affected_count': affected_count,
        'message': f'{action.capitalize()} completed for {affected_count} workers'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_job_action(request):
    """
    Perform bulk actions on jobs.

    Request body:
        {
            "job_ids": [1, 2, 3],
            "action": "reject" | "close" | "delete"
        }

    Note: ServiceRequest has no "approved"/"featured" state - requests go
    live as 'pending' immediately on creation, so there is nothing for an
    "approve"/"feature" action to do. Those actions were removed rather
    than kept as silent no-ops that reported success.
    """
    job_ids = request.data.get('job_ids', [])
    action = request.data.get('action')
    reason = request.data.get('reason', '')

    if not job_ids:
        return Response({
            'error': 'job_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)

    valid_actions = ['reject', 'close', 'delete']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)

    jobs = ServiceRequest.objects.filter(id__in=job_ids)
    affected_count = 0

    with transaction.atomic():
        if action == 'reject':
            affected_count = jobs.update(status='cancelled')

        elif action == 'close':
            affected_count = jobs.update(status='cancelled')

        elif action == 'delete':
            affected_count = jobs.count()
            jobs.delete()
    
    return Response({
        'success': True,
        'action': action,
        'affected_count': affected_count,
        'message': f'{action.capitalize()} completed for {affected_count} jobs'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_application_action(request):
    """
    Perform bulk actions on job applications.
    
    Request body:
        {
            "application_ids": [1, 2, 3],
            "action": "approve" | "reject"
        }

    Note: "shortlist" was removed - JobApplication.STATUS_CHOICES has no
    'shortlisted' value, so it wrote a status nothing else in the app
    recognizes or ever transitions out of.
    """
    application_ids = request.data.get('application_ids', [])
    action = request.data.get('action')

    if not application_ids:
        return Response({
            'error': 'application_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)

    valid_actions = ['approve', 'reject']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)

    applications = JobApplication.objects.filter(id__in=application_ids)
    affected_count = 0

    status_map = {
        'approve': 'accepted',
        'reject': 'rejected',
    }
    
    with transaction.atomic():
        affected_count = applications.update(status=status_map[action])
    
    return Response({
        'success': True,
        'action': action,
        'affected_count': affected_count,
        'message': f'{action.capitalize()} completed for {affected_count} applications'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_send_notification(request):
    """
    Send notifications to multiple users.
    
    Request body:
        {
            "user_ids": [1, 2, 3] OR "user_type": "worker" | "client" | "all",
            "subject": "Important Update",
            "message": "Message content",
            "notification_type": "email" | "push" | "both"
        }

    Note: push notification delivery is not implemented anywhere in this
    codebase (device push tokens are registered but nothing ever sends to
    them), so "push"/"both" requests still only produce an in-app +
    email notification - the response says so via "warning" rather than
    silently claiming success for a push that never went out.
    """
    user_ids = request.data.get('user_ids', [])
    user_type = request.data.get('user_type')
    subject = request.data.get('subject')
    message = request.data.get('message')
    notification_type = request.data.get('notification_type', 'email')

    if not subject or not message:
        return Response({
            'error': 'subject and message are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get users
    if user_ids:
        users = User.objects.filter(id__in=user_ids, is_active=True)
    elif user_type == 'worker':
        users = User.objects.filter(
            worker_profile__isnull=False,
            is_active=True
        )
    elif user_type == 'client':
        users = User.objects.filter(
            client_profile__isnull=False,
            is_active=True
        )
    elif user_type == 'all':
        users = User.objects.filter(is_active=True)
    else:
        return Response({
            'error': 'Either user_ids or user_type required'
        }, status=status.HTTP_400_BAD_REQUEST)

    total_users = users.count()
    sent_count = 0
    failed_count = 0

    # Routed through NotificationService so this creates a real in-app
    # Notification (visible in the app + over websocket) and a properly
    # addressed email via settings.DEFAULT_FROM_EMAIL, instead of the
    # previous raw send_mass_mail() call that left no record and hardcoded
    # a fake from-address.
    for user in users:
        try:
            NotificationService.create_notification(
                recipient=user,
                title=subject,
                message=message,
                notification_type='system_alert',
            )
            sent_count += 1
        except Exception:
            failed_count += 1

    response_data = {
        'success': True,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'total_users': total_users,
        'message': f'Notification sent to {sent_count} users',
    }
    if notification_type in ('push', 'both'):
        response_data['warning'] = (
            'Push delivery is not implemented; recipients received an '
            'in-app + email notification only.'
        )

    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_export_users(request):
    """
    Export user data in bulk.
    
    Request body:
        {
            "user_type": "worker" | "client" | "all",
            "format": "json" | "csv",
            "fields": ["email", "name", "created_at"]  // optional
        }
    """
    from django.http import HttpResponse
    import json
    import csv
    from io import StringIO
    
    user_type = request.data.get('user_type', 'all')
    export_format = request.data.get('format', 'json')
    fields = request.data.get('fields', ['id', 'email', 'first_name', 'last_name', 'date_joined', 'is_active'])
    
    # Get users
    if user_type == 'worker':
        users = User.objects.filter(worker_profile__isnull=False)
    elif user_type == 'client':
        users = User.objects.filter(client_profile__isnull=False)
    else:
        users = User.objects.all()
    
    # Filter superusers for security
    users = users.exclude(is_superuser=True)
    
    # Build data
    data = []
    for user in users:
        row = {}
        for field in fields:
            if hasattr(user, field):
                value = getattr(user, field)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row[field] = value
        data.append(row)
    
    if export_format == 'csv':
        output = StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        
        return Response({
            'format': 'csv',
            'data': output.getvalue(),
            'count': len(data),
        })
    
    return Response({
        'format': 'json',
        'data': data,
        'count': len(data),
    })
