from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max
from django.utils import timezone
from jobs.models import Conversation, Message
from jobs.serializers import ConversationSerializer, MessageSerializer
from worker_connect.notification_service import NotificationService

class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_list(request):
    """Get user's conversations with latest message info"""
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).annotate(
        latest_message_time=Max('messages__created_at')
    ).order_by('-latest_message_time')
    
    conversation_data = []
    for conv in conversations:
        # Get the other participant
        other_participant = conv.participant2 if conv.participant1 == request.user else conv.participant1
        
        # Get latest message
        latest_message = conv.messages.order_by('-created_at').first()
        
        # Get unread count
        unread_count = conv.messages.filter(
            sender__ne=request.user,
            is_read=False
        ).count()
        
        conversation_data.append({
            'id': conv.id,
            'other_participant': {
                'id': other_participant.id,
                'name': other_participant.get_full_name(),
                'email': other_participant.email,
                'profile_image': getattr(other_participant.worker_profile if hasattr(other_participant, 'worker_profile') else other_participant.client_profile if hasattr(other_participant, 'client_profile') else None, 'profile_image', None)
            },
            'latest_message': {
                'content': latest_message.content if latest_message else None,
                'created_at': latest_message.created_at if latest_message else conv.created_at,
                'sender_name': latest_message.sender.get_full_name() if latest_message else None,
                'is_from_me': latest_message.sender == request.user if latest_message else False
            },
            'unread_count': unread_count,
            'job_request': {
                'id': conv.job_request.id,
                'title': conv.job_request.title
            } if conv.job_request else None,
            'updated_at': conv.updated_at
        })
    
    return Response({
        'success': True,
        'conversations': conversation_data,
        'total_unread': sum(c['unread_count'] for c in conversation_data)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, conversation_id):
    """Get conversation details with messages"""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id
    )
    
    # Check if user is participant
    if request.user not in [conversation.participant1, conversation.participant2]:
        return Response({
            'success': False,
            'error': 'You are not a participant in this conversation'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get messages with pagination
    messages = conversation.messages.order_by('-created_at')
    
    paginator = MessagePagination()
    page = paginator.paginate_queryset(messages, request)
    
    if page is not None:
        # Mark messages as read
        conversation.messages.filter(
            sender__ne=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        serializer = MessageSerializer(page, many=True)
        
        # Get other participant info
        other_participant = (
            conversation.participant2 
            if conversation.participant1 == request.user 
            else conversation.participant1
        )
        
        response_data = {
            'conversation': {
                'id': conversation.id,
                'other_participant': {
                    'id': other_participant.id,
                    'name': other_participant.get_full_name(),
                    'email': other_participant.email,
                    'is_online': getattr(other_participant, 'is_online', False),
                    'last_seen': getattr(other_participant, 'last_seen', None),
                },
                'job_request': {
                    'id': conversation.job_request.id,
                    'title': conversation.job_request.title,
                    'status': conversation.job_request.status
                } if conversation.job_request else None,
                'created_at': conversation.created_at
            },
            'messages': serializer.data
        }
        
        return paginator.get_paginated_response(response_data)
    
    return Response({
        'success': False,
        'error': 'No messages found'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Send a new message"""
    conversation_id = request.data.get('conversation_id')
    content = request.data.get('content', '').strip()
    
    if not conversation_id:
        return Response({
            'success': False,
            'error': 'Conversation ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not content:
        return Response({
            'success': False,
            'error': 'Message content is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get conversation
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if user is participant
    if request.user not in [conversation.participant1, conversation.participant2]:
        return Response({
            'success': False,
            'error': 'You are not a participant in this conversation'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Create message
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )
    
    # Update conversation timestamp
    conversation.updated_at = timezone.now()
    conversation.save()
    
    # Send notification to other participant
    recipient = (
        conversation.participant2 
        if conversation.participant1 == request.user 
        else conversation.participant1
    )
    
    NotificationService.notify_message_received(
        conversation=conversation,
        sender=request.user,
        recipient=recipient
    )
    
    # Serialize message
    serializer = MessageSerializer(message)
    
    return Response({
        'success': True,
        'message': serializer.data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_conversation(request):
    """Start a new conversation"""
    other_user_id = request.data.get('other_user_id')
    job_request_id = request.data.get('job_request_id')
    initial_message = request.data.get('initial_message', '').strip()
    
    if not other_user_id:
        return Response({
            'success': False,
            'error': 'Other user ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if other_user == request.user:
        return Response({
            'success': False,
            'error': 'Cannot start conversation with yourself'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if conversation already exists
    existing_conversation = Conversation.objects.filter(
        Q(participant1=request.user, participant2=other_user) |
        Q(participant1=other_user, participant2=request.user)
    ).first()
    
    if existing_conversation:
        return Response({
            'success': True,
            'conversation_id': existing_conversation.id,
            'message': 'Conversation already exists'
        })
    
    # Get job request if provided
    job_request = None
    if job_request_id:
        try:
            from jobs.models import JobRequest
            job_request = JobRequest.objects.get(id=job_request_id)
        except JobRequest.DoesNotExist:
            pass
    
    # Create new conversation
    conversation = Conversation.objects.create(
        participant1=request.user,
        participant2=other_user,
        job_request=job_request
    )
    
    # Send initial message if provided
    if initial_message:
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=initial_message
        )
        
        # Send notification
        NotificationService.notify_message_received(
            conversation=conversation,
            sender=request.user,
            recipient=other_user
        )
    
    return Response({
        'success': True,
        'conversation_id': conversation.id,
        'message': 'Conversation started successfully'
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_messages_read(request, conversation_id):
    """Mark all messages in conversation as read"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if user is participant
    if request.user not in [conversation.participant1, conversation.participant2]:
        return Response({
            'success': False,
            'error': 'You are not a participant in this conversation'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Mark messages as read
    updated_count = conversation.messages.filter(
        sender__ne=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({
        'success': True,
        'message': f'Marked {updated_count} messages as read'
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_message(request, message_id):
    """Delete a message (soft delete)"""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save()
    
    return Response({
        'success': True,
        'message': 'Message deleted successfully'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_conversations(request):
    \"\"\"Search conversations by participant name or message content\"\"\"
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response({
            'success': False,
            'error': 'Search query is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Search conversations by participant name
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).filter(
        Q(participant1__first_name__icontains=query) |
        Q(participant1__last_name__icontains=query) |
        Q(participant2__first_name__icontains=query) |
        Q(participant2__last_name__icontains=query) |
        Q(messages__content__icontains=query)
    ).distinct().order_by('-updated_at')[:20]
    
    serializer = ConversationSerializer(conversations, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'conversations': serializer.data,
        'query': query
    })