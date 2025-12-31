"""
Admin bulk action views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mass_mail

from accounts.models import User
from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.models import JobRequest, JobApplication


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
                    user.worker_profile.is_verified = True
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
            affected_count = workers.update(is_verified=True)
        
        elif action == 'unverify':
            affected_count = workers.update(is_verified=False)
        
        elif action == 'feature':
            affected_count = workers.update(is_featured=True)
        
        elif action == 'unfeature':
            affected_count = workers.update(is_featured=False)
        
        elif action == 'suspend':
            # Deactivate user accounts
            for worker in workers:
                worker.user.is_active = False
                worker.user.save()
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
            "action": "approve" | "reject" | "close" | "delete" | "feature"
        }
    """
    job_ids = request.data.get('job_ids', [])
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    
    if not job_ids:
        return Response({
            'error': 'job_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valid_actions = ['approve', 'reject', 'close', 'delete', 'feature', 'unfeature']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    jobs = JobRequest.objects.filter(id__in=job_ids)
    affected_count = 0
    
    with transaction.atomic():
        if action == 'approve':
            affected_count = jobs.update(status='open')
        
        elif action == 'reject':
            affected_count = jobs.update(status='rejected')
        
        elif action == 'close':
            affected_count = jobs.update(status='closed')
        
        elif action == 'delete':
            affected_count = jobs.count()
            jobs.delete()
        
        elif action == 'feature':
            affected_count = jobs.update(is_featured=True)
        
        elif action == 'unfeature':
            affected_count = jobs.update(is_featured=False)
    
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
            "action": "approve" | "reject" | "shortlist"
        }
    """
    application_ids = request.data.get('application_ids', [])
    action = request.data.get('action')
    
    if not application_ids:
        return Response({
            'error': 'application_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valid_actions = ['approve', 'reject', 'shortlist']
    if action not in valid_actions:
        return Response({
            'error': f'Invalid action. Must be one of: {valid_actions}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    applications = JobApplication.objects.filter(id__in=application_ids)
    affected_count = 0
    
    status_map = {
        'approve': 'accepted',
        'reject': 'rejected',
        'shortlist': 'shortlisted',
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
    
    sent_count = 0
    failed_count = 0
    
    if notification_type in ['email', 'both']:
        # Prepare email messages
        emails = []
        for user in users.exclude(email=''):
            emails.append((
                subject,
                message,
                'noreply@workerconnect.com',
                [user.email],
            ))
        
        # Send in batches
        try:
            sent_count = send_mass_mail(emails, fail_silently=True)
        except Exception as e:
            failed_count = len(emails)
    
    if notification_type in ['push', 'both']:
        # Push notification logic would go here
        # This is a placeholder for push notification service integration
        pass
    
    return Response({
        'success': True,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'total_users': users.count(),
        'message': f'Notification sent to {sent_count} users'
    })


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
