"""
API endpoints for messaging system
Handles conversations between Workers, Clients, and Admins
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Max, Count
from django.utils import timezone
from .models import Message
from accounts.models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """Get list of conversations for the current user"""
    user = request.user
    
    # Get all users the current user has conversations with
    sent_to = Message.objects.filter(sender=user).values_list('recipient', flat=True).distinct()
    received_from = Message.objects.filter(recipient=user).values_list('sender', flat=True).distinct()
    
    # Combine and get unique user IDs
    conversation_user_ids = set(list(sent_to) + list(received_from))
    
    conversations = []
    for user_id in conversation_user_ids:
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            continue
        
        # Get last message
        last_message = Message.objects.filter(
            Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
        ).order_by('-created_at').first()
        
        # Count unread messages
        unread_count = Message.objects.filter(
            sender=other_user,
            recipient=user,
            is_read=False
        ).count()
        
        conversations.append({
            'id': other_user.id,
            'name': other_user.get_full_name() or other_user.username,
            'username': other_user.username,
            'user_type': other_user.user_type,
            'last_message': last_message.message if last_message else '',
            'last_message_time': last_message.created_at.isoformat() if last_message else None,
            'unread_count': unread_count,
            'is_online': False,  # TODO: Implement online status
        })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x['last_message_time'] or '', reverse=True)
    
    return Response({'conversations': conversations})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    """Get all messages between current user and specified user"""
    user = request.user
    
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all messages between these two users
    messages = Message.objects.filter(
        Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
    ).order_by('created_at')
    
    # Mark messages as read
    Message.objects.filter(
        sender=other_user,
        recipient=user,
        is_read=False
    ).update(is_read=True)
    
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'sender_type': msg.sender.user_type,
            'recipient_id': msg.recipient.id,
            'recipient_name': msg.recipient.get_full_name() or msg.recipient.username,
            'message': msg.message,
            'subject': msg.subject,
            'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
            'created_at': msg.created_at.isoformat(),
            'is_sent_by_me': msg.sender.id == user.id,
        })
    
    return Response({
        'messages': messages_data,
        'other_user': {
            'id': other_user.id,
            'name': other_user.get_full_name() or other_user.username,
            'username': other_user.username,
            'user_type': other_user.user_type,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_api(request):
    """Send a message to another user"""
    user = request.user
    
    recipient_id = request.data.get('recipient_id')
    message_text = request.data.get('message', '').strip()
    subject = request.data.get('subject', '').strip()
    
    if not recipient_id:
        return Response({'error': 'Recipient ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not message_text:
        return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        recipient = User.objects.get(id=recipient_id)
    except User.DoesNotExist:
        return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Create message
    message = Message.objects.create(
        sender=user,
        recipient=recipient,
        message=message_text,
        subject=subject,
    )
    
    return Response({
        'success': True,
        'message': {
            'id': message.id,
            'sender_id': message.sender.id,
            'sender_name': message.sender.get_full_name() or message.sender.username,
            'recipient_id': message.recipient.id,
            'recipient_name': message.recipient.get_full_name() or message.recipient.username,
            'message': message.message,
            'subject': message.subject,
            'is_read': message.is_read,
            'created_at': message.created_at.isoformat(),
            'is_sent_by_me': True,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Get total unread message count for current user"""
    user = request.user
    
    unread_count = Message.objects.filter(
        recipient=user,
        is_read=False
    ).count()
    
    return Response({'unread_count': unread_count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, message_id):
    """Mark a specific message as read"""
    user = request.user
    
    try:
        message = Message.objects.get(id=message_id, recipient=user)
        message.is_read = True
        message.save()
        
        return Response({'success': True, 'message': 'Message marked as read'})
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Search for users to start a conversation with"""
    user = request.user
    
    query = request.GET.get('q', '').strip()
    user_type = request.GET.get('type', '')  # 'worker', 'client', 'admin'
    
    users = User.objects.exclude(id=user.id)
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    if user_type:
        users = users.filter(user_type=user_type)
    
    users = users[:20]  # Limit to 20 results
    
    users_data = []
    for u in users:
        users_data.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'username': u.username,
            'user_type': u.user_type,
        })
    
    return Response({'users': users_data})
