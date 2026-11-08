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
    from .views import _conversation_list
    from .chat_access import is_admin
    me_admin = is_admin(request.user)
    conversations = []
    for c in _conversation_list(request.user):
        other, last = c['user'], c['last_message']
        name = other.get_full_name() or (other.username if me_admin else 'Worker Connect')
        conversations.append({
            'id': other.id,
            'name': name,
            # username is the sign-up e-mail: only staff get it
            'username': other.username if me_admin else name,
            'user_type': 'admin' if c['is_support'] else other.user_type,
            'last_message': last.message if last else '',
            'last_message_time': last.created_at.isoformat() if last else None,
            'unread_count': c['unread_count'],
            'is_online': False,
            'about': c['about'],
            'can_send': c['can_send'],
            # filled only for a worker/client with an accepted job together
            'phone_number': c['call_phone'],
        })

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
    
    from .chat_access import can_chat, is_admin, call_number
    allowed = can_chat(user, other_user)
    messages = (Message.objects.filter(
        Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user))
        .select_related('sender', 'recipient').order_by('created_at'))
    # Strangers get nothing - not even a name (this used to hand out anyone's
    # e-mail address for any user id).
    if not allowed and not messages.exists():
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    Message.objects.filter(sender=other_user, recipient=user, is_read=False).update(
        is_read=True, read_at=timezone.now())

    me_admin = is_admin(user)

    def name_of(u):
        return u.get_full_name() or (u.username if me_admin or u.pk == user.pk else 'Worker Connect')

    messages_data = [{
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': name_of(msg.sender),
        'sender_type': msg.sender.user_type,
        'recipient_id': msg.recipient_id,
        'recipient_name': name_of(msg.recipient),
        'message': msg.message,
        'subject': msg.subject,
        'is_read': msg.is_read,
        'created_at': msg.created_at.isoformat(),
        'is_sent_by_me': msg.sender_id == user.id,
    } for msg in messages]

    return Response({
        'messages': messages_data,
        'can_send': allowed,
        'other_user': {
            'id': other_user.id,
            'name': name_of(other_user),
            'username': other_user.username if me_admin else name_of(other_user),
            'user_type': 'admin' if is_admin(other_user) else other_user.user_type,
            'phone_number': call_number(user, other_user),
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
        recipient = User.objects.get(id=int(recipient_id))
    except (User.DoesNotExist, ValueError, TypeError):  # "abc" used to be a 500
        return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)

    from .chat_access import can_chat, CLOSED_REASON
    if not can_chat(user, recipient):
        return Response({'error': CLOSED_REASON}, status=status.HTTP_403_FORBIDDEN)

    # Create message
    message = Message.objects.create(
        sender=user,
        recipient=recipient,
        message=message_text,
        subject=subject,
    )

    # Notify the recipient in real time (websocket + email) - this is the
    # live send endpoint the mobile app actually calls.
    from .chat_access import notify_new_message
    notify_new_message(message)

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
        message.read_at = message.read_at or timezone.now()
        message.save(update_fields=['is_read', 'read_at'])
        
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
    
    users = User.objects.filter(is_active=True).exclude(id=user.id)

    # username is the e-mail address for every API sign-up, so searching or
    # returning it let any account harvest everyone's e-mail - staff
    # included. Only staff see it; everyone else finds people by name.
    from .chat_access import is_admin
    is_staff = is_admin(user)
    if query:
        name_match = Q(first_name__icontains=query) | Q(last_name__icontains=query)
        if is_staff:
            name_match |= Q(username__icontains=query) | Q(email__icontains=query)
        users = users.filter(name_match)
    elif not is_staff:
        return Response({'users': []})

    if user_type:
        users = users.filter(user_type=user_type)

    # Workers and clients may only find support and the people whose job was accepted.
    if not is_staff:
        from .chat_access import chat_partners
        users = users.filter(Q(is_staff=True) | Q(user_type='admin') | Q(id__in=list(chat_partners(user).keys())))

    users = users[:20]  # Limit to 20 results

    users_data = []
    for u in users:
        entry = {
            'id': u.id,
            'name': u.get_full_name() or (u.username if is_staff else f'User {u.id}'),
            'user_type': u.user_type,
        }
        if is_staff:
            entry['username'] = u.username
        users_data.append(entry)
    
    return Response({'users': users_data})
