from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import JobRequest, JobApplication, Message
from .forms import JobRequestForm, JobApplicationForm, MessageForm
from workers.models import Category
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
            
            # Update client profile
            profile = request.user.client_profile
            profile.total_jobs_posted += 1
            profile.save()
            
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

@login_required
def inbox(request):
    """View inbox messages - WhatsApp style conversation list"""
    from django.db.models import Q, Max, Count
    
    # For workers and clients, they only see conversations with admin
    # For admin, they see all conversations with workers and clients
    
    if request.user.is_staff or request.user.user_type == 'admin':
        # Admin sees all messages involving them
        all_messages = Message.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        )
        
        # Group by conversation partner
        conversations = {}
        for msg in all_messages:
            # Determine the other person in conversation
            other_user = msg.recipient if msg.sender == request.user else msg.sender
            
            if other_user.id not in conversations:
                conversations[other_user.id] = {
                    'user': other_user,
                    'messages': [],
                    'unread_count': 0,
                }
            
            conversations[other_user.id]['messages'].append(msg)
            
            # Count unread messages from this person
            if msg.recipient == request.user and not msg.is_read:
                conversations[other_user.id]['unread_count'] += 1
        
        # Sort messages in each conversation and get last message
        conversation_list = []
        for conv_data in conversations.values():
            conv_data['messages'].sort(key=lambda x: x.created_at, reverse=True)
            conv_data['last_message'] = conv_data['messages'][0]
            conv_data['total_messages'] = len(conv_data['messages'])
            conversation_list.append(conv_data)
        
        # Sort conversations by last message time
        conversation_list.sort(key=lambda x: x['last_message'].created_at, reverse=True)
    else:
        # Workers and clients only see conversation with admin
        # Get admin user (first staff user)
        admin_user = User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).first()
        
        if admin_user:
            all_messages = Message.objects.filter(
                Q(sender=request.user, recipient=admin_user) |
                Q(sender=admin_user, recipient=request.user)
            ).order_by('-created_at')
            
            unread_count = all_messages.filter(
                recipient=request.user,
                is_read=False
            ).count()
            
            conversation_list = [{
                'user': admin_user,
                'messages': list(all_messages),
                'unread_count': unread_count,
                'last_message': all_messages.first() if all_messages.exists() else None,
                'total_messages': all_messages.count(),
            }] if all_messages.exists() or True else []  # Always show admin conversation
        else:
            conversation_list = []
    
    # Determine which base template to use
    if request.user.is_staff or request.user.user_type == 'admin':
        base_template = 'admin_panel/base_admin.html'
    else:
        base_template = 'workers/base_worker.html' if hasattr(request.user, 'worker_profile') else 'clients/base_client.html'
    
    context = {
        'conversations': conversation_list,
        'base_template': base_template,
    }
    return render(request, 'jobs/inbox.html', context)


@login_required
def send_message(request, recipient_id):
    """Send a message to another user - redirects to conversation"""
    # Workers and clients can only message admin
    # Admins can message anyone
    
    if request.user.is_staff or request.user.user_type == 'admin':
        # Admin can message the specified recipient
        recipient = get_object_or_404(User, pk=recipient_id)
        return redirect('jobs:conversation', user_id=recipient_id)
    else:
        # Workers and clients always redirect to admin conversation
        admin_user = User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).first()
        if admin_user:
            return redirect('jobs:conversation', user_id=admin_user.id)
        else:
            messages.error(request, 'No admin available to contact.')
            return redirect('jobs:inbox')


@login_required
def conversation(request, user_id):
    """View conversation thread with a specific user (WhatsApp style)"""
    
    other_user = get_object_or_404(User, pk=user_id)
    
    # Security check: Workers and clients can only chat with admin
    if not (request.user.is_staff or request.user.user_type == 'admin'):
        # Non-admin users can only chat with admin
        if not (other_user.is_staff or other_user.user_type == 'admin'):
            # Redirect to admin conversation instead
            admin_user = User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).first()
            if admin_user:
                messages.warning(request, 'You can only message the admin. Direct messaging between workers and clients is not allowed.')
                return redirect('jobs:conversation', user_id=admin_user.id)
            else:
                messages.error(request, 'No admin available to contact.')
                return redirect('jobs:inbox')
    
    # Get all messages between current user and other user
    messages_list = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).order_by('created_at')
    
    # Mark all messages from other user as read
    Message.objects.filter(
        sender=other_user,
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    # Handle new message submission
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = other_user
            message.save()
            
            messages.success(request, 'Message sent!')
            return redirect('jobs:conversation', user_id=user_id)
    else:
        form = MessageForm()
    
    # Determine which base template to use
    if request.user.is_staff or request.user.user_type == 'admin':
        base_template = 'admin_panel/base_admin.html'
    else:
        base_template = 'workers/base_worker.html' if hasattr(request.user, 'worker_profile') else 'clients/base_client.html'
    
    context = {
        'other_user': other_user,
        'messages_list': messages_list,
        'form': form,
        'base_template': base_template,
    }
    return render(request, 'jobs/conversation.html', context)


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
