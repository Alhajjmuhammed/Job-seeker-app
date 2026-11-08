"""
Worker verification in one place.

The queue lists workers with real filters, and one review page shows a
worker's profile and every document with its decision buttons, so an admin
approves the ID and verifies the worker without leaving the page. Before,
the queue's filter buttons did nothing, documents were approved on a
separate page, and the worker was never told about any decision.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from workers.models import WorkerDocument, WorkerProfile

STATUSES = ('pending', 'verified', 'rejected')


def _notify(worker, title, message, kind='account_update'):
    """Tell the worker in the app and by e-mail. Never blocks the decision."""
    try:
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(
            recipient=worker.user, title=title, message=message,
            notification_type=kind,
            extra_data={'action': 'open_documents'},
        )
    except Exception:  # pragma: no cover - a notification problem must not undo the decision
        import logging
        logging.getLogger(__name__).exception('Could not notify worker %s', worker.pk)


def _queue(params):
    workers = (WorkerProfile.objects.select_related('user')
               .prefetch_related('categories')
               .annotate(docs_total=Count('documents', distinct=True),
                         docs_pending=Count('documents', filter=Q(documents__verification_status='pending'), distinct=True),
                         docs_approved=Count('documents', filter=Q(documents__verification_status='approved'), distinct=True),
                         docs_rejected=Count('documents', filter=Q(documents__verification_status='rejected'), distinct=True)))

    status = params.get('status', 'pending')
    if status in STATUSES:
        workers = workers.filter(verification_status=status)
    else:
        status = 'all'

    docs = params.get('docs', '')
    if docs == 'waiting':
        workers = workers.filter(docs_pending__gt=0)
    elif docs == 'none':
        workers = workers.filter(docs_total=0)
    else:
        docs = ''

    q = params.get('q', '').strip()
    if q:
        workers = workers.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) | Q(user__username__icontains=q) |
            Q(user__phone_number__icontains=q) | Q(city__icontains=q)
        )

    # documents waiting first, then oldest sign-ups first (fair queue)
    workers = workers.order_by('-docs_pending', 'created_at')
    return workers, status, docs, q


@staff_member_required
def worker_verification_list(request):
    workers, status, docs, q = _queue(request.GET)
    page = Paginator(workers, 25).get_page(request.GET.get('page'))

    counts = WorkerProfile.objects.aggregate(
        all=Count('id'),
        pending=Count('id', filter=Q(verification_status='pending')),
        verified=Count('id', filter=Q(verification_status='verified')),
        rejected=Count('id', filter=Q(verification_status='rejected')),
    )
    counts['docs_waiting'] = WorkerProfile.objects.filter(documents__verification_status='pending').distinct().count()

    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'admin_panel/worker_verification_list.html', {
        'page': page, 'status': status, 'docs': docs, 'q': q,
        'counts': counts, 'query': query.urlencode(),
    })


def _next_pending(after):
    """The next worker still waiting for a decision, for "Next" on the review page."""
    queue = (WorkerProfile.objects.filter(verification_status='pending')
             .annotate(docs_pending=Count('documents', filter=Q(documents__verification_status='pending')))
             .order_by('-docs_pending', 'created_at')
             .exclude(pk=after.pk))
    return queue.first()


@staff_member_required
def review_worker(request, worker_id):
    worker = get_object_or_404(WorkerProfile.objects.select_related('user', 'agent__user'), pk=worker_id)

    if request.method == 'POST':
        _decide(request, worker)
        if request.POST.get('then') == 'next':
            nxt = _next_pending(worker)
            if nxt:
                return redirect('admin_panel:verify_worker', worker_id=nxt.pk)
            messages.info(request, 'No more workers waiting for review.')
            return redirect('admin_panel:worker_verification_list')
        return redirect('admin_panel:verify_worker', worker_id=worker.pk)

    documents = list(worker.documents.order_by('document_type', '-uploaded_at'))
    for doc in documents:
        name = (doc.file.name or '').lower()
        doc.is_image = name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        doc.is_pdf = name.endswith('.pdf')
    id_docs = [d for d in documents if d.document_type == 'id']

    return render(request, 'admin_panel/verify_worker.html', {
        'worker': worker,
        'documents': documents,
        'has_id': bool(id_docs),
        'id_approved': any(d.verification_status == 'approved' for d in id_docs),
        'id_pending': next((d for d in id_docs if d.verification_status == 'pending'), None),
        'next_worker': _next_pending(worker),
        'queue_left': WorkerProfile.objects.filter(verification_status='pending').count(),
    })


def _decide(request, worker):
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()
    name = worker.user.get_full_name() or worker.user.username

    if action in ('approve_doc', 'reject_doc'):
        doc_id = request.POST.get('doc_id', '')
        if not str(doc_id).isdigit():  # a non-number crashed the page with a 500
            from django.http import Http404
            raise Http404
        doc = get_object_or_404(WorkerDocument, pk=int(doc_id), worker=worker)
        if action == 'approve_doc':
            _approve_document(doc)
            messages.success(request, f'{doc.get_document_type_display()} approved.')
        else:
            if not reason:
                messages.error(request, 'Please give a reason, so the worker knows what to fix.')
                return
            doc.verification_status = 'rejected'
            doc.rejection_reason = reason
            doc.verified_at = None
            doc.save(update_fields=['verification_status', 'rejection_reason', 'verified_at'])
            _notify(worker, 'Document needs attention',
                    f'Your {doc.get_document_type_display().split(" (")[0]} was not accepted: {reason}. '
                    'Please upload a new one from your profile.', kind='document_verified')
            messages.warning(request, f'{doc.get_document_type_display()} rejected.')
        return

    if action in ('verify', 'approve_id_and_verify'):
        if action == 'approve_id_and_verify':
            pending_id = worker.documents.filter(document_type='id', verification_status='pending').first()
            if pending_id:
                _approve_document(pending_id, notify=False)
        if not worker.documents.filter(document_type='id', verification_status='approved').exists():
            messages.error(request, f'{name} needs an approved ID document before they can be verified.')
            return
        worker.verification_status = 'verified'
        worker.save(update_fields=['verification_status'])
        _notify(worker, 'You are verified ✅',
                'Your Worker Connect account is verified. You can now be assigned to jobs.')
        messages.success(request, f'{name} is verified.')
        return

    if action == 'reject':
        if not reason:
            messages.error(request, 'Please give a reason, so the worker knows what to fix.')
            return
        worker.verification_status = 'rejected'
        worker.save(update_fields=['verification_status'])
        _notify(worker, 'Verification not approved',
                f'Your account could not be verified: {reason}. Update your profile and documents, then contact support.')
        messages.warning(request, f'{name} was rejected.')
        return

    if action == 'reopen':
        worker.verification_status = 'pending'
        worker.save(update_fields=['verification_status'])
        messages.info(request, f'{name} is back in the queue.')


def _approve_document(doc, notify=True):
    doc.verification_status = 'approved'
    doc.verified_at = timezone.now()
    doc.rejection_reason = ''
    doc.save(update_fields=['verification_status', 'verified_at', 'rejection_reason'])
    if notify:
        _notify(doc.worker, 'Document approved',
                f'Your {doc.get_document_type_display().split(" (")[0]} has been approved.', kind='document_verified')


@staff_member_required
def document_verification_list(request):
    """Documents are reviewed on each worker's page; this lists who has some waiting."""
    url = reverse('admin_panel:worker_verification_list') + '?status=all&docs=waiting'
    worker_id = request.GET.get('worker')
    if worker_id and worker_id.isdigit():
        url = reverse('admin_panel:verify_worker', kwargs={'worker_id': int(worker_id)})
    return redirect(url)


@staff_member_required
def verify_document(request, doc_id):
    """Old per-document page: decisions now happen on the worker's review page."""
    doc = get_object_or_404(WorkerDocument, pk=doc_id)
    if request.method == 'POST':
        post = request.POST.copy()
        post['doc_id'] = str(doc.pk)
        post['action'] = {'approve': 'approve_doc', 'reject': 'reject_doc'}.get(post.get('action'), post.get('action'))
        request.POST = post
        _decide(request, doc.worker)
    return redirect('admin_panel:verify_worker', worker_id=doc.worker_id)


@staff_member_required
def admin_search(request):
    """The search box in the admin header: one query across people and bookings."""
    from accounts.models import User
    from agents.models import AgentProfile
    from jobs.service_request_models import ServiceRequest

    q = request.GET.get('q', '').strip()
    results = {'workers': [], 'clients': [], 'agents': [], 'requests': []}
    if q:
        person = (Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) |
                  Q(username__icontains=q) | Q(phone_number__icontains=q))
        if ' ' in q:  # "Asha Juma" as a full name
            first, last = q.split(' ', 1)
            person |= Q(first_name__icontains=first, last_name__icontains=last)
        users = User.objects.filter(person)
        results['workers'] = list(WorkerProfile.objects.filter(Q(user__in=users) | Q(city__icontains=q))
                                  .select_related('user').distinct()[:20])
        results['clients'] = list(users.filter(user_type='client')[:20])
        results['agents'] = list(AgentProfile.objects.filter(Q(user__in=users) | Q(agent_code__iexact=q))
                                 .select_related('user').distinct()[:20])
        req = Q(title__icontains=q) | Q(client__in=users) | Q(city__icontains=q) | Q(payment_transaction_id__iexact=q)
        if q.lstrip('#').isdigit():
            req |= Q(pk=int(q.lstrip('#')))
        results['requests'] = list(ServiceRequest.objects.filter(req).select_related('client', 'category')
                                   .distinct().order_by('-created_at')[:20])

    return render(request, 'admin_panel/search.html', {
        'q': q, 'results': results, 'total': sum(len(v) for v in results.values()),
    })
