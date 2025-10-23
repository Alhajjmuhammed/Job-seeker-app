"""
Context processors for providing global template variables
"""
from django.db.models import Q
from workers.models import WorkerProfile, WorkerDocument
from jobs.models import Message


def admin_counts(request):
    """
    Provide counts for admin panel sidebar badges
    """
    context = {}
    
    if request.user.is_authenticated:
        # Only calculate for admin users
        if request.user.is_staff or request.user.user_type == 'admin':
            # Pending workers verification
            context['pending_workers_count'] = WorkerProfile.objects.filter(
                verification_status='pending'
            ).count()
            
            # Pending documents verification
            context['pending_documents_count'] = WorkerDocument.objects.filter(
                verification_status='pending'
            ).count()
            
            # Unread messages for admin
            context['unread_messages_count'] = Message.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
        else:
            # For workers and clients
            context['pending_workers_count'] = 0
            context['pending_documents_count'] = 0
            
            # Unread messages from admin
            admin_user = request.user.__class__.objects.filter(
                Q(is_staff=True) | Q(user_type='admin')
            ).first()
            
            if admin_user:
                context['unread_messages_count'] = Message.objects.filter(
                    sender=admin_user,
                    recipient=request.user,
                    is_read=False
                ).count()
            else:
                context['unread_messages_count'] = 0
    else:
        context['pending_workers_count'] = 0
        context['pending_documents_count'] = 0
        context['unread_messages_count'] = 0
    
    return context
