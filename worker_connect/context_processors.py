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
    return {'SCRIPT_PREFIX': request.META.get('SCRIPT_NAME', ''), 'UI_VERSION': _ui_version()}


_UI_VERSION = None


def _ui_version():
    """
    Short fingerprint of static/css/ui.css. The web server tells browsers to keep
    static files for 30 days, so the layouts link ui.css?v=<this>: a new version
    of the file gets a new address and every browser fetches it at once.
    """
    global _UI_VERSION
    if _UI_VERSION is None:
        import hashlib
        from pathlib import Path
        from django.conf import settings
        try:
            data = (Path(settings.BASE_DIR) / 'static' / 'css' / 'ui.css').read_bytes()
            _UI_VERSION = hashlib.md5(data).hexdigest()[:8]
        except OSError:
            _UI_VERSION = '1'
    return _UI_VERSION


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

            # Job posts waiting for review
            from jobs.vacancy_models import Vacancy
            context['pending_vacancies_count'] = Vacancy.objects.filter(status='review').count()

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


            # Unread chat messages - from support and from workers/clients they work with
            context['unread_messages_count'] = Message.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
    else:
        context['pending_workers_count'] = 0
        context['pending_documents_count'] = 0
        context['pending_service_requests_count'] = 0
        context['unread_messages_count'] = 0
    
    return context
