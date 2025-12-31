"""
Messaging system for Worker Connect.

Enables in-app messaging between clients and workers.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Max, Count, OuterRef, Subquery
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """
    Get list of conversations for the authenticated user.
    
    Returns conversations with last message preview and unread count.
    """
    from jobs.models import Message
    
    user = request.user
    
    # Get conversations where user is participant
    # A conversation is identified by the job_request + the two participants
    conversations_qs = Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).values(
        'job_request_id'
    ).annotate(
        last_message_time=Max('created_at'),
        message_count=Count('id'),
    ).order_by('-last_message_time')
    
    conversations = []
    for conv in conversations_qs:
        job_id = conv['job_request_id']
        
        # Get the last message
        last_message = Message.objects.filter(
            job_request_id=job_id
        ).filter(
            Q(sender=user) | Q(recipient=user)
        ).order_by('-created_at').first()
        
        if not last_message:
            continue
        
        # Determine the other participant
        other_user = last_message.recipient if last_message.sender == user else last_message.sender
        
        # Count unread messages
        unread_count = Message.objects.filter(
            job_request_id=job_id,
            recipient=user,
            is_read=False
        ).count()
        
        conversations.append({
            'job_id': job_id,
            'job_title': last_message.job_request.title if last_message.job_request else 'Direct Message',
            'other_user': {
                'id': other_user.id,
                'name': f"{other_user.first_name} {other_user.last_name}",
                'user_type': other_user.user_type,
            },
            'last_message': {
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'sent_by_me': last_message.sender == user,
                'created_at': last_message.created_at.isoformat(),
            },
            'unread_count': unread_count,
            'total_messages': conv['message_count'],
        })
    
    return Response({
        'conversations': conversations,
        'total_unread': sum(c['unread_count'] for c in conversations),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, job_id):
    """
    Get messages for a specific job/conversation.
    
    Query params:
        - page: Page number (default: 1)
        - page_size: Messages per page (default: 50)
        - before_id: Get messages before this ID (for pagination)
    """
    from jobs.models import Message, JobRequest
    
    user = request.user
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 50)), 100)
    before_id = request.query_params.get('before_id')
    
    # Verify user has access to this conversation
    try:
        job = JobRequest.objects.get(id=job_id)
        # User must be job poster or have applied to job
        is_job_owner = job.client.user == user
        is_applicant = hasattr(user, 'worker_profile') and job.jobapplication_set.filter(
            worker=user.worker_profile
        ).exists()
        
        if not (is_job_owner or is_applicant):
            return Response(
                {'error': 'You do not have access to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get messages
    messages = Message.objects.filter(
        job_request_id=job_id
    ).filter(
        Q(sender=user) | Q(recipient=user)
    ).select_related('sender', 'recipient').order_by('-created_at')
    
    if before_id:
        messages = messages.filter(id__lt=before_id)
    
    total_count = messages.count()
    start = (page - 1) * page_size
    messages = messages[start:start + page_size]
    
    # Mark messages as read
    Message.objects.filter(
        job_request_id=job_id,
        recipient=user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({
        'messages': [
            {
                'id': msg.id,
                'content': msg.content,
                'sender': {
                    'id': msg.sender.id,
                    'name': f"{msg.sender.first_name} {msg.sender.last_name}",
                    'is_me': msg.sender == user,
                },
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
            }
            for msg in messages
        ],
        'total_count': total_count,
        'has_more': total_count > start + page_size,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, job_id):
    """
    Send a message in a job conversation.
    
    Body:
        - content: Message content (required)
        - recipient_id: Recipient user ID (optional, determined automatically for jobs)
    """
    from jobs.models import Message, JobRequest
    
    user = request.user
    content = request.data.get('content', '').strip()
    
    if not content:
        return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if len(content) > 5000:
        return Response({'error': 'Message too long (max 5000 characters)'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get job and determine recipient
    try:
        job = JobRequest.objects.select_related('client__user').get(id=job_id)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Determine recipient
    is_job_owner = job.client.user == user
    
    if is_job_owner:
        # Job owner is sending to a worker - need recipient_id
        recipient_id = request.data.get('recipient_id')
        if not recipient_id:
            return Response(
                {'error': 'recipient_id is required for job owners'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Worker is sending to job owner
        recipient = job.client.user
        
        # Verify worker has applied
        if hasattr(user, 'worker_profile'):
            has_applied = job.jobapplication_set.filter(worker=user.worker_profile).exists()
            if not has_applied:
                return Response(
                    {'error': 'You must apply to the job before messaging'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'Only workers can message job owners'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Create message
    message = Message.objects.create(
        job_request=job,
        sender=user,
        recipient=recipient,
        content=content,
    )
    
    # Send real-time notification if available
    try:
        from worker_connect.websocket_consumers import send_user_notification
        from worker_connect.push_notifications import PushNotificationService, NotificationTemplates
        
        # WebSocket notification
        send_user_notification(recipient.id, {
            'type': 'new_message',
            'message_id': message.id,
            'job_id': job_id,
            'sender_name': f"{user.first_name} {user.last_name}",
            'preview': content[:100],
        })
        
        # Push notification
        template = NotificationTemplates.message_received(f"{user.first_name} {user.last_name}")
        # Would need device token from recipient's profile
        
    except Exception as e:
        pass  # Notifications are optional
    
    return Response({
        'message': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'recipient_id': recipient.id,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Get total unread message count for the user."""
    from jobs.models import Message
    
    count = Message.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return Response({'unread_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request, job_id):
    """Mark all messages in a conversation as read."""
    from jobs.models import Message
    
    updated = Message.objects.filter(
        job_request_id=job_id,
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({'marked_read': updated})
