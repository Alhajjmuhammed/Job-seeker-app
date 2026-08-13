"""
Context processors for providing global template variables
"""
from django.db.models import Q
from workers.models import WorkerProfile, WorkerDocument
from jobs.models import Message
from jobs.service_request_models import ServiceRequest


def script_prefix(request):
    """
    Expose the app's URL prefix (empty unless reverse-proxied under a
    subpath, e.g. /wc) so inline JS can build correct absolute paths
    instead of hardcoding root-relative ones.
    """
    return {'SCRIPT_PREFIX': request.META.get('SCRIPT_NAME', '')}


def admin_counts(request):
    """
    Provide counts for admin panel sidebar badges
    """
    context = {}
    
    # Safety check: ensure request has user attribute
    if not hasattr(request, 'user'):
        return context
    
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

            # Pending service requests awaiting assignment
            context['pending_service_requests_count'] = ServiceRequest.objects.filter(
                status='pending'
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
            context['pending_service_requests_count'] = 0


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
        context['pending_service_requests_count'] = 0
        context['unread_messages_count'] = 0
    
    return context
