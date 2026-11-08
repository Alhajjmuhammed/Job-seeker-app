from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import JobRequest, JobApplication, Message, DirectHireRequest
from .forms import JobRequestForm, JobApplicationForm, MessageForm, DirectHireRequestForm
from workers.models import Category, WorkerProfile
from accounts.models import User


# Job Request Views (Client)

@login_required
def job_list(request):
    """List all jobs (different views for client and worker)"""
    if request.user.is_client:
        jobs = JobRequest.objects.filter(client=request.user).select_related('category')
    elif request.user.is_worker:
        jobs = JobRequest.objects.filter(status='open').exclude(
            applications__worker__user=request.user
        ).select_related('category')
    else:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        jobs = jobs.filter(category_id=category_id)
    
    duration = request.GET.get('duration')
    if duration:
        jobs = jobs.filter(duration=duration)
    
    status = request.GET.get('status')
    if status and request.user.is_client:
        jobs = jobs.filter(status=status)
    
    budget_min = request.GET.get('budget_min')
    if budget_min:
        jobs = jobs.filter(budget__gte=budget_min)
    
    budget_max = request.GET.get('budget_max')
    if budget_max:
        jobs = jobs.filter(budget__lte=budget_max)
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by not in ('-created_at', 'created_at', '-budget', 'budget'):
        sort_by = '-created_at'  # anything else would error out or order by a hidden field
    jobs = jobs.order_by(sort_by)
    
    categories = Category.objects.all()
    
    # Calculate statistics
    total_jobs = jobs.count()
    open_jobs = jobs.filter(status='open').count()
    in_progress_jobs = jobs.filter(status='in_progress').count()
    completed_jobs = jobs.filter(status='completed').count()
    
    # Determine which base template to use
    base_template = 'workers/base_worker.html' if hasattr(request.user, 'worker_profile') else 'clients/base_client.html'
    
    context = {
        'jobs': jobs,
        'categories': categories,
        'base_template': base_template,
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
    }
    
    return render(request, 'jobs/job_list.html', context)


@login_required
def job_detail(request, pk):
    """View job details"""
    job = get_object_or_404(JobRequest, pk=pk)
    
    # Admin can view all jobs
    is_admin = request.user.is_staff or request.user.user_type == 'admin'
    
    # Check if worker has applied
    has_applied = False
    if request.user.is_worker:
        has_applied = JobApplication.objects.filter(
            job=job,
            worker__user=request.user
        ).exists()
    
    # Show applications to client and admin
    applications = job.applications.all() if (request.user == job.client or is_admin) else None
    
    # Determine which base template to use
    if is_admin:
        base_template = 'admin_panel/base_admin.html'
    elif hasattr(request.user, 'worker_profile'):
        base_template = 'workers/base_worker.html'
    else:
        base_template = 'clients/base_client.html'
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'applications': applications,
        'base_template': base_template,
        'is_admin': is_admin,
    }
    return render(request, 'jobs/job_detail.html', context)


@login_required
def job_create(request):
    """Create a new job request (clients only)"""
    if not request.user.is_client:
        messages.error(request, 'Only clients can post jobs.')
        return redirect('home')
    
    if request.method == 'POST':
        form = JobRequestForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user
            job.save()
            
            # Update client profile. A freshly-registered client has no
            # ClientProfile row yet (it's created lazily elsewhere, not at
            # registration), so this must not assume one exists - unlike
            # every other call site doing this same update, this one wasn't
            # guarded and would 500 for a brand-new client's first post.
            if not hasattr(request.user, 'client_profile'):
                from clients.models import ClientProfile
                ClientProfile.objects.get_or_create(user=request.user)
            # JobRequest is the deprecated model and has no post_save
            # totals hook, but ClientProfile.total_jobs_posted counts
            # ServiceRequests - incrementing it here made the stored
            # number disagree with the requests it claims to count.
            
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobRequestForm()
    
    context = {
        'form': form,
        'action': 'Create',
        'base_template': 'clients/base_client.html',
        'active_menu': 'post_job'
    }
    return render(request, 'jobs/job_form.html', context)


@login_required
def job_edit(request, pk):
    """Edit a job request"""
    job = get_object_or_404(JobRequest, pk=pk, client=request.user)
    
    if request.method == 'POST':
        form = JobRequestForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobRequestForm(instance=job)
    
    context = {
        'form': form,
        'action': 'Edit',
        'job': job,
        'base_template': 'clients/base_client.html',
        'active_menu': 'my_jobs'
    }
    return render(request, 'jobs/job_form.html', context)


@login_required
def job_delete(request, pk):
    """Delete a job request"""
    job = get_object_or_404(JobRequest, pk=pk, client=request.user)
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('jobs:job_list')
    
    return render(request, 'jobs/job_delete.html', {'job': job})


@login_required
def job_close(request, pk):
    """Close/complete a job"""
    job = get_object_or_404(JobRequest, pk=pk, client=request.user)
    
    if request.method == 'POST':
        if job.status in ('completed', 'cancelled'):
            messages.warning(request, f'This job is already {job.get_status_display().lower()}.')
            return redirect('jobs:job_detail', pk=job.pk)

        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()

        if job.assigned_worker:
            job.assigned_worker.completed_jobs += 1
            job.assigned_worker.save()
        
        messages.success(request, 'Job marked as completed!')
        return redirect('jobs:job_detail', pk=job.pk)
    
    return render(request, 'jobs/job_close.html', {'job': job})


# Job Application Views (Worker)

@login_required
def apply_for_job(request, pk):
    """Apply for a job (workers only)"""
    if not request.user.is_worker:
        messages.error(request, 'Only workers can apply for jobs.')
        return redirect('home')
    
    job = get_object_or_404(JobRequest, pk=pk)
    worker_profile = request.user.worker_profile
    
    # Check if worker is verified
    if worker_profile.verification_status == 'rejected':
        messages.error(request, 'Your profile has been rejected. You cannot apply for jobs. Please contact support.')
        return redirect('jobs:job_detail', pk=pk)
    elif worker_profile.verification_status == 'pending':
        messages.warning(request, 'Your profile is under review. You can apply once verified.')
        return redirect('jobs:job_detail', pk=pk)
    
    if job.status != 'open':  # cancelled / finished jobs took applications too
        messages.error(request, 'This job is no longer taking applications.')
        return redirect('jobs:job_detail', pk=pk)

    # Check if already applied
    if JobApplication.objects.filter(job=job, worker=worker_profile).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('jobs:job_detail', pk=pk)
    
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.worker = worker_profile
            application.save()
            
            worker_profile.total_jobs += 1
            worker_profile.save()
            
            messages.success(request, 'Application submitted successfully!')
            return redirect('jobs:my_applications')
    else:
        form = JobApplicationForm()
    
    return render(request, 'jobs/apply_for_job.html', {'form': form, 'job': job})


@login_required
def my_applications(request):
    """View worker's job applications"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    applications = JobApplication.objects.filter(
        worker__user=request.user
    ).select_related('job', 'job__client', 'job__category').order_by('-created_at')
    
    # Calculate statistics
    total_apps = applications.count()
    pending_apps = applications.filter(status='pending').count()
    accepted_apps = applications.filter(status='accepted').count()
    rejected_apps = applications.filter(status='rejected').count()
    
    context = {
        'applications': applications,
        'total_apps': total_apps,
        'pending_apps': pending_apps,
        'accepted_apps': accepted_apps,
        'rejected_apps': rejected_apps,
    }
    
    return render(request, 'jobs/my_applications.html', context)


@login_required
def application_detail(request, pk):
    """View application details"""
    application = get_object_or_404(JobApplication, pk=pk)
    
    # Check permissions
    if not (request.user == application.job.client or 
            request.user == application.worker.user):
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return render(request, 'jobs/application_detail.html', {'application': application})


@login_required
def accept_application(request, pk):
    """Accept a job application (clients only)"""
    application = get_object_or_404(JobApplication, pk=pk)
    
    if request.user != application.job.client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if request.method == 'POST':
        # only a pending application on a job that is still open (a withdrawn application,
        # or a job already in progress / cancelled, could be "accepted" before)
        if application.status != 'pending' or application.job.status != 'open':
            messages.error(request, 'This application can no longer be accepted.')
            return redirect('jobs:job_detail', pk=application.job.pk)
        application.status = 'accepted'
        application.save()
        
        # Assign worker to job
        job = application.job
        job.assigned_worker = application.worker
        job.status = 'in_progress'
        job.save()
        
        # Reject other applications
        JobApplication.objects.filter(job=job).exclude(pk=pk).update(status='rejected')
        
        messages.success(request, 'Application accepted!')
        return redirect('jobs:job_detail', pk=job.pk)
    
    return render(request, 'jobs/accept_application.html', {'application': application})


@login_required
def reject_application(request, pk):
    """Reject a job application (clients only)"""
    application = get_object_or_404(JobApplication, pk=pk)
    
    if request.user != application.job.client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if request.method == 'POST':
        application.status = 'rejected'
        application.save()
        
        messages.success(request, 'Application rejected.')
        return redirect('jobs:job_detail', pk=application.job.pk)
    
    return redirect('jobs:job_detail', pk=application.job.pk)


# Messaging Views

def _chat_base_template(user):
    from .chat_access import is_admin
    if is_admin(user):
        return 'admin_panel/base_admin.html'
    if getattr(user, 'user_type', '') == 'agent':
        return 'agents/base_agents.html'
    return 'workers/base_worker.html' if hasattr(user, 'worker_profile') else 'clients/base_client.html'


def _conversation_list(user):
    """
    Everyone this user has a chat with, newest first: people they have
    messages with, plus (for workers and clients) support and every
    worker/client whose job was accepted - even before the first message.
    """
    from .chat_access import is_admin, chat_partners, support_user

    admin_view = is_admin(user)
    partners = {} if admin_view else chat_partners(user)
    convs = {}

    def entry(other):
        if other.id not in convs:
            convs[other.id] = {'user': other, 'last_message': None, 'unread_count': 0,
                               'about': partners.get(other.id, ''),
                               'is_support': is_admin(other),
                               'can_send': other.is_active and (admin_view or is_admin(other) or other.id in partners),
                               # who may be phoned: an accepted-job partner (admins: anyone)
                               'call_phone': (other.phone_number or '') if other.is_active and (
                                   (admin_view and not is_admin(other)) or other.id in partners) else ''}
        return convs[other.id]

    # One row per chat partner, worked out in the database (this list is
    # rebuilt every few seconds while a chat page is open).
    from django.db.models import Case, When, F, Max, Count, IntegerField
    rows = (Message.objects.filter(Q(sender=user) | Q(recipient=user))
            .exclude(sender=F('recipient'))  # notes to self are not a chat
            .annotate(other=Case(When(sender=user, then=F('recipient_id')), default=F('sender_id'),
                                 output_field=IntegerField()))
            .values('other')
            .annotate(last_id=Max('id'), unread=Count('id', filter=Q(recipient=user, is_read=False))))
    rows = list(rows)
    if rows:
        lasts = Message.objects.in_bulk([r['last_id'] for r in rows])
        people = User.objects.in_bulk([r['other'] for r in rows])
        for r in rows:
            other = people.get(r['other'])
            if other is None:
                continue
            c = entry(other)
            c['last_message'] = lasts.get(r['last_id'])
            c['unread_count'] = r['unread']

    if not admin_view:
        support = support_user()
        if support and not any(c['is_support'] for c in convs.values()):
            entry(support)
        if partners:
            for other in User.objects.filter(id__in=partners.keys(), is_active=True):
                entry(other)

    today = timezone.localdate()
    for c in convs.values():
        m = c['last_message']
        c['time_label'] = _day_label(m.created_at, today, short=True) if m else ''

    def order(c):
        m = c['last_message']
        return (m is not None, m.created_at if m else timezone.now())
    return sorted(convs.values(), key=order, reverse=True)


def _day_label(when, today, short=False):
    from django.utils.translation import gettext as _
    from django.utils.formats import date_format
    local = timezone.localtime(when)
    d = local.date()
    if d == today:
        return local.strftime('%H:%M') if short else _('Today')
    if (today - d).days == 1:
        return _('Yesterday')
    return date_format(local, 'j M' if short else 'l, j F Y')


@login_required
def inbox(request):
    """Chat list. On a wide screen the empty right pane explains who you can chat with."""
    from .chat_access import is_admin
    return render(request, 'jobs/inbox.html', {
        'conversations': _conversation_list(request.user),
        'base_template': _chat_base_template(request.user),
        'other_user': None,
        'me_admin': is_admin(request.user),
    })


@login_required
def send_message(request, recipient_id):
    """Old "send message" links: open the chat with that person if allowed, else support."""
    from .chat_access import can_chat, support_user
    other = get_object_or_404(User, pk=recipient_id)
    if can_chat(request.user, other):
        return redirect('jobs:conversation', user_id=other.id)
    support = support_user()
    if support and support.pk != request.user.pk:
        return redirect('jobs:conversation', user_id=support.id)
    messages.error(request, 'No admin available to contact.')
    return redirect('jobs:inbox')


@login_required
def conversation(request, user_id):
    """One chat thread, shown next to the chat list."""
    from .chat_access import can_chat, is_admin, call_number, CLOSED_REASON

    other_user = get_object_or_404(User, pk=user_id)
    if other_user.pk == request.user.pk:
        return redirect('jobs:inbox')

    messages_list = (Message.objects.filter(
        Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user))
        .select_related('sender').order_by('created_at'))
    allowed = can_chat(request.user, other_user)

    if not allowed and not messages_list.exists() and request.method == 'GET':
        messages.warning(request, CLOSED_REASON)
        return redirect('jobs:inbox')

    Message.objects.filter(sender=other_user, recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now())

    if request.method == 'POST':
        if not allowed:
            messages.error(request, CLOSED_REASON)
            return redirect('jobs:conversation', user_id=user_id)
        text = (request.POST.get('message') or '').strip()
        if text:
            from .chat_access import notify_new_message
            notify_new_message(Message.objects.create(sender=request.user, recipient=other_user, message=text[:5000]))
        return redirect('jobs:conversation', user_id=user_id)

    thread = list(messages_list)
    today, last_day = timezone.localdate(), None
    for msg in thread:
        day = timezone.localtime(msg.created_at).date()
        msg.day_label = _day_label(msg.created_at, today) if day != last_day else ''
        last_day = day
    conversations = _conversation_list(request.user)
    current = next((c for c in conversations if c['user'].id == other_user.id), None)
    return render(request, 'jobs/inbox.html', {
        'conversations': conversations,
        'base_template': _chat_base_template(request.user),
        'other_user': other_user,
        'other_is_admin': is_admin(other_user),
        'current': current,
        'messages_list': thread,
        'thread_sig': f"{len(thread)}-{sum(1 for m in thread if m.is_read)}",
        'me_admin': is_admin(request.user),
        'can_send': allowed,
        'call_phone': call_number(request.user, other_user),
        'closed_reason': CLOSED_REASON,
    })


@login_required
def message_detail(request, pk):
    """View message details"""
    message = get_object_or_404(Message, pk=pk)
    
    if request.user not in [message.sender, message.recipient]:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Mark as read if recipient
    if request.user == message.recipient and not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'jobs/message_detail.html', {'message': message})


# ===============================================
# DIRECT HIRE / ON-DEMAND BOOKING VIEWS
# ===============================================

def _suggested_rate(worker):
    """A sensible opening offer for hiring this worker directly.

    Work is priced per request, so the suggestion is what the platform charges
    for one worker in this worker's own category - never an hourly figure.
    """
    category = worker.categories.first()
    return category.daily_rate if category else None


@login_required
def request_worker_directly(request, worker_id):
    """Client requests/books a worker directly for quick work"""
    if not request.user.is_client:
        messages.error(request, 'Only clients can request workers.')
        return redirect('home')
    
    worker = get_object_or_404(WorkerProfile, pk=worker_id)
    
    # Check if worker can accept direct hires
    if not worker.can_accept_direct_hires:
        messages.error(request, 'This worker is not available for direct hire requests. They need to upload ID and be verified.')
        return redirect('workers:public_profile', pk=worker_id)
    
    if request.method == 'POST':
        form = DirectHireRequestForm(request.POST, suggested_rate=_suggested_rate(worker))
        if form.is_valid():
            direct_hire = form.save(commit=False)
            direct_hire.client = request.user
            direct_hire.worker = worker
            direct_hire.save()
            from worker_connect.notification_service import NotificationService
            NotificationService.notify_direct_hire(direct_hire)
            
            messages.success(request, f'Request sent to {worker.user.get_full_name()}! They will be notified.')
            return redirect('jobs:direct_hire_detail', pk=direct_hire.pk)
    else:
        form = DirectHireRequestForm(suggested_rate=_suggested_rate(worker))
    
    context = {
        'form': form,
        'worker': worker,
    }
    return render(request, 'jobs/direct_hire_request_form.html', context)


@login_required
def direct_hire_detail(request, pk):
    """View details of a direct hire request"""
    hire_request = get_object_or_404(DirectHireRequest, pk=pk)
    
    # Check access
    if request.user not in [hire_request.client, hire_request.worker.user]:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    context = {
        'hire_request': hire_request,
        'is_worker': request.user == hire_request.worker.user,
        'is_client': request.user == hire_request.client,
        'can_cancel': hire_request.can_cancel(request.user),
    }
    return render(request, 'jobs/direct_hire_detail.html', context)


@login_required
def cancel_direct_hire(request, pk):
    """Client (pending/accepted) or worker (accepted) cancels a direct booking."""
    hire_request = get_object_or_404(DirectHireRequest, pk=pk)
    if request.user not in (hire_request.client, hire_request.worker.user):
        messages.error(request, 'Access denied.')
        return redirect('home')
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()[:500]
        if hire_request.cancel(request.user, reason):
            messages.success(request, 'The booking was cancelled. The other side has been told.')
        else:
            messages.error(request, 'This booking can no longer be cancelled.')
    return redirect('jobs:direct_hire_detail', pk=pk)


@login_required
def worker_accept_direct_hire(request, pk):
    """Worker accepts a direct hire request"""
    hire_request = get_object_or_404(DirectHireRequest, pk=pk)
    
    # Check if user is the worker
    if not hasattr(request.user, 'worker_profile') or request.user.worker_profile != hire_request.worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Check if already responded
    if hire_request.status != 'pending':
        messages.warning(request, 'This request has already been responded to.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    if request.method == 'POST':
        response_message = request.POST.get('response_message', '')
        
        hire_request.status = 'accepted'
        hire_request.worker_response_message = response_message
        hire_request.responded_at = timezone.now()
        hire_request.save()
        
        # Update worker availability
        hire_request.worker.availability = 'busy'
        hire_request.worker.save()
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_direct_hire(hire_request)
        
        messages.success(request, 'Request accepted! The client will be notified.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    return render(request, 'jobs/direct_hire_accept.html', {'hire_request': hire_request})


@login_required
def worker_reject_direct_hire(request, pk):
    """Worker rejects a direct hire request"""
    hire_request = get_object_or_404(DirectHireRequest, pk=pk)
    
    # Check if user is the worker
    if not hasattr(request.user, 'worker_profile') or request.user.worker_profile != hire_request.worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Check if already responded
    if hire_request.status != 'pending':
        messages.warning(request, 'This request has already been responded to.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        hire_request.status = 'rejected'
        hire_request.worker_response_message = reason
        hire_request.responded_at = timezone.now()
        hire_request.save()
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_direct_hire(hire_request)
        
        messages.info(request, 'Request declined.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    return render(request, 'jobs/direct_hire_reject.html', {'hire_request': hire_request})


@login_required
def my_direct_hire_requests(request):
    """List direct hire requests (different view for client and worker)"""
    
    if request.user.is_client:
        # Client sees requests they've sent
        hire_requests = DirectHireRequest.objects.filter(client=request.user).select_related('worker__user')
        template = 'jobs/client_direct_hires.html'
    elif hasattr(request.user, 'worker_profile'):
        # Worker sees requests they've received
        hire_requests = DirectHireRequest.objects.filter(worker=request.user.worker_profile).select_related('client')
        template = 'jobs/worker_direct_requests.html'
    else:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Count over everything, before the filter is applied. Counting the
    # filtered queryset made every other tab read zero as soon as one was
    # selected, so the tabs could not be used to navigate.
    status_counts = {
        'pending': hire_requests.filter(status='pending').count(),
        'accepted': hire_requests.filter(status='accepted').count(),
        'rejected': hire_requests.filter(status='rejected').count(),
        'completed': hire_requests.filter(status='completed').count(),
    }

    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        hire_requests = hire_requests.filter(status=status_filter)

    hire_requests = hire_requests.order_by('-created_at')
    
    context = {
        'hire_requests': hire_requests,
        'status_filter': status_filter,
        'status_counts': status_counts,
    }
    return render(request, template, context)


@login_required
def complete_direct_hire(request, pk):
    """Client marks direct hire as completed and can rate worker"""
    hire_request = get_object_or_404(DirectHireRequest, pk=pk)
    
    # Only client can complete
    if request.user != hire_request.client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if hire_request.status != 'accepted':
        messages.error(request, 'Can only complete accepted requests.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback', '')

        try:
            rating_value = int(rating)
        except (TypeError, ValueError):
            rating_value = None

        from django.db import transaction
        with transaction.atomic():
            if DirectHireRequest.objects.select_for_update().get(pk=hire_request.pk).status != 'accepted':
                messages.error(request, 'This booking is no longer active.')
                return redirect('jobs:direct_hire_detail', pk=pk)
            hire_request.status = 'completed'
            hire_request.completed_at = timezone.now()
            hire_request.save(update_fields=['status', 'completed_at', 'updated_at'])
        hire_request.status = 'completed'
        hire_request.completed_at = timezone.now()
        # the parsed number, 1-5 only (the raw text crashed on '' / 'abc', and stored 9 as 9)
        hire_request.client_rating = rating_value if rating_value and 1 <= rating_value <= 5 else None
        hire_request.client_feedback = feedback
        hire_request.save()

        # Update worker stats
        worker = hire_request.worker
        worker.completed_jobs += 1
        worker.total_jobs += 1
        worker.total_earnings += hire_request.total_amount

        # Persist the rating as a real Rating row so it actually counts
        # toward the worker's average and shows up in their review list -
        # previously only hire_request.client_rating was set, which nothing
        # else ever read.
        from clients.models import Rating
        if rating_value and 1 <= rating_value <= 5:
            Rating.objects.update_or_create(
                client=request.user,
                worker=worker,
                defaults={'rating': rating_value, 'review': feedback},
            )

        ratings = Rating.objects.filter(worker=worker)
        if ratings.exists():
            from django.db.models import Avg
            avg = ratings.aggregate(Avg('rating'))['rating__avg']
            worker.average_rating = round(avg, 2)
            worker.total_reviews = ratings.count()

        worker.save()

        # Free the worker only if nothing else keeps them busy (an active job-post contract,
        # a booking, or another accepted direct hire) - this used to set "available" always.
        hire_request.free_worker_if_idle()
        
        messages.success(request, 'Work completed! Thank you for your feedback.')
        return redirect('jobs:direct_hire_detail', pk=pk)
    
    return render(request, 'jobs/direct_hire_complete.html', {'hire_request': hire_request})
