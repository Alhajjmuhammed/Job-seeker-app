from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import csv
import json

from accounts.models import User
from workers.models import WorkerProfile, WorkerDocument, Category, Skill
from clients.models import ClientProfile, Rating
from jobs.models import JobRequest, Message


@staff_member_required
def dashboard(request):
    """Admin dashboard with statistics"""
    
    # User statistics
    total_users = User.objects.count()
    total_workers = User.objects.filter(user_type='worker').count()
    total_clients = User.objects.filter(user_type='client').count()
    
    # Worker statistics
    verified_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    pending_verification = WorkerProfile.objects.filter(verification_status='pending').count()
    available_workers = WorkerProfile.objects.filter(availability='available').count()
    
    # Job statistics
    total_jobs = JobRequest.objects.count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    
    # Recent activities
    recent_workers = WorkerProfile.objects.order_by('-created_at')[:5]
    recent_jobs = JobRequest.objects.order_by('-created_at')[:5]
    pending_documents = WorkerDocument.objects.filter(verification_status='pending')[:10]
    
    context = {
        'total_users': total_users,
        'total_workers': total_workers,
        'total_clients': total_clients,
        'verified_workers': verified_workers,
        'pending_verification': pending_verification,
        'available_workers': available_workers,
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'completed_jobs': completed_jobs,
        'recent_workers': recent_workers,
        'recent_jobs': recent_jobs,
        'pending_documents': pending_documents,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@staff_member_required
def worker_verification_list(request):
    """List workers pending verification"""
    workers = WorkerProfile.objects.all().order_by('-created_at')
    
    # Get counts for statistics
    pending_count = workers.filter(verification_status='pending').count()
    verified_count = workers.filter(verification_status='verified').count()
    rejected_count = workers.filter(verification_status='rejected').count()
    
    context = {
        'workers': workers,
        'pending_count': pending_count,
        'verified_count': verified_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'admin_panel/worker_verification_list.html', context)


@staff_member_required
def verify_worker(request, worker_id):
    """Verify a worker"""
    worker = get_object_or_404(WorkerProfile, pk=worker_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            worker.verification_status = 'verified'
            worker.save()
            messages.success(request, f'Worker {worker.user.get_full_name()} has been verified.')
        elif action == 'approve':
            worker.verification_status = 'verified'
            worker.save()
            messages.success(request, f'Worker {worker.user.get_full_name()} has been verified.')
        elif action == 'reject':
            worker.verification_status = 'rejected'
            reason = request.POST.get('reason', '')
            worker.save()
            messages.warning(request, f'Worker {worker.user.get_full_name()} has been rejected.')
        
        # Check if we came from document verification page
        referer = request.META.get('HTTP_REFERER', '')
        if 'documents/verification' in referer:
            return redirect('admin_panel:document_verification_list')
        else:
            return redirect('admin_panel:worker_verification_list')
    
    return render(request, 'admin_panel/verify_worker.html', {'worker': worker})


@staff_member_required
def document_verification_list(request):
    """List documents grouped by worker"""
    # Get selected worker from query params
    selected_worker_id = request.GET.get('worker')
    
    # Get counts for statistics
    pending_count = WorkerDocument.objects.filter(verification_status='pending').count()
    approved_count = WorkerDocument.objects.filter(verification_status='approved').count()
    rejected_count = WorkerDocument.objects.filter(verification_status='rejected').count()
    total_count = WorkerDocument.objects.count()
    
    if selected_worker_id:
        # Show documents for selected worker
        selected_worker = get_object_or_404(WorkerProfile, id=selected_worker_id)
        documents = WorkerDocument.objects.filter(
            worker=selected_worker
        ).order_by('-uploaded_at')
        
        context = {
            'documents': documents,
            'selected_worker': selected_worker,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'total_count': total_count,
        }
    else:
        # Show list of workers with document counts
        from django.db.models import Count, Q
        
        workers_with_docs = WorkerProfile.objects.filter(
            documents__isnull=False
        ).distinct().annotate(
            total_docs=Count('documents'),
            pending_docs=Count('documents', filter=Q(documents__verification_status='pending')),
            approved_docs=Count('documents', filter=Q(documents__verification_status='approved')),
            rejected_docs=Count('documents', filter=Q(documents__verification_status='rejected'))
        ).order_by('user__first_name')
        
        context = {
            'workers_with_docs': workers_with_docs,
            'selected_worker': None,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'total_count': total_count,
        }
    
    return render(request, 'admin_panel/document_verification_list.html', context)


@staff_member_required
def verify_document(request, doc_id):
    """Verify a document"""
    document = get_object_or_404(WorkerDocument, pk=doc_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            document.verification_status = 'approved'
            document.verified_at = timezone.now()
            document.save()
            messages.success(request, 'Document approved.')
        elif action == 'reject':
            document.verification_status = 'rejected'
            document.rejection_reason = request.POST.get('reason', '')
            document.save()
            messages.warning(request, 'Document rejected.')
        
        return redirect('admin_panel:document_verification_list')
    
    return render(request, 'admin_panel/verify_document.html', {'document': document})


@staff_member_required
def category_list(request):
    """Manage categories"""
    categories = Category.objects.annotate(
        worker_count=Count('workers'),
        job_count=Count('jobs')
    )
    return render(request, 'admin_panel/category_list.html', {'categories': categories})


@staff_member_required
def reports(request):
    """Generate reports and analytics"""
    import json
    from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
    
    # Get filter parameters
    days = int(request.GET.get('days', 30))
    view_type = request.GET.get('view', 'daily')  # daily, weekly, monthly, yearly
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Determine truncation function based on view type
    if view_type == 'daily':
        trunc_func = TruncDate('date_joined')
        date_format = '%Y-%m-%d'
        label_format = '%b %d'  # Nov 09
    elif view_type == 'weekly':
        trunc_func = TruncWeek('date_joined')
        date_format = '%Y-W%W'
        label_format = 'Week %W'  # Week 45
    elif view_type == 'monthly':
        trunc_func = TruncMonth('date_joined')
        date_format = '%Y-%m'
        label_format = '%b %Y'  # Nov 2025
    elif view_type == 'yearly':
        trunc_func = TruncYear('date_joined')
        date_format = '%Y'
        label_format = '%Y'  # 2025
    else:
        trunc_func = TruncDate('date_joined')
        date_format = '%Y-%m-%d'
        label_format = '%b %d'
    
    # Registration trends - Get user registrations grouped by selected period
    user_registrations = User.objects.filter(
        date_joined__gte=start_date
    ).annotate(
        period=trunc_func
    ).values('period').annotate(
        workers=Count('id', filter=Q(user_type='worker')),
        clients=Count('id', filter=Q(user_type='client')),
        total=Count('id')
    ).order_by('period')
    
    # Prepare chart data
    chart_labels = []
    worker_data = []
    client_data = []
    total_data = []
    
    for item in user_registrations:
        if item['period']:
            # Format label based on view type
            if view_type == 'weekly':
                week_num = item['period'].isocalendar()[1]
                chart_labels.append(f"Week {week_num}")
            else:
                chart_labels.append(item['period'].strftime(label_format))
            
            worker_data.append(item['workers'])
            client_data.append(item['clients'])
            total_data.append(item['total'])
    
    # Convert to JSON for JavaScript
    chart_data = {
        'labels': chart_labels,
        'workers': worker_data,
        'clients': client_data,
        'total': total_data,
        'view_type': view_type
    }
    
    # Statistics for the period
    new_workers = WorkerProfile.objects.filter(created_at__gte=start_date).count()
    new_clients = ClientProfile.objects.filter(created_at__gte=start_date).count()
    new_jobs = JobRequest.objects.filter(created_at__gte=start_date).count()
    
    # Calculate growth percentages
    previous_start = start_date - timedelta(days=days)
    prev_workers = WorkerProfile.objects.filter(
        created_at__gte=previous_start, 
        created_at__lt=start_date
    ).count()
    prev_clients = ClientProfile.objects.filter(
        created_at__gte=previous_start, 
        created_at__lt=start_date
    ).count()
    prev_jobs = JobRequest.objects.filter(
        created_at__gte=previous_start, 
        created_at__lt=start_date
    ).count()
    
    users_growth = round(((new_workers + new_clients - prev_workers - prev_clients) / 
                          (prev_workers + prev_clients) * 100), 1) if (prev_workers + prev_clients) > 0 else 0
    workers_growth = round(((new_workers - prev_workers) / prev_workers * 100), 1) if prev_workers > 0 else 0
    jobs_growth = round(((new_jobs - prev_jobs) / prev_jobs * 100), 1) if prev_jobs > 0 else 0
    
    # Top categories
    top_categories = Category.objects.annotate(
        worker_count=Count('workers')
    ).order_by('-worker_count')[:5]
    
    # Top rated workers
    top_workers = WorkerProfile.objects.filter(
        verification_status='verified'
    ).order_by('-average_rating')[:10]
    
    # Job completion rate
    total_jobs = JobRequest.objects.filter(created_at__gte=start_date).count()
    completed = JobRequest.objects.filter(
        created_at__gte=start_date,
        status='completed'
    ).count()
    completion_rate = round((completed / total_jobs * 100), 2) if total_jobs > 0 else 0
    completed_growth = round(((completed - prev_jobs) / prev_jobs * 100), 1) if prev_jobs > 0 else 0
    
    # Recent users for display
    recent_users = User.objects.filter(
        date_joined__gte=start_date
    ).order_by('-date_joined')[:10]
    
    # Additional statistics
    total_users = User.objects.count()
    active_workers = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).count()
    verified_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    pending_workers = WorkerProfile.objects.filter(verification_status='pending').count()
    available_workers = WorkerProfile.objects.filter(availability='available').count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    in_progress_jobs = JobRequest.objects.filter(status='in_progress').count()
    assigned_jobs = JobRequest.objects.filter(assigned_worker__isnull=False).count()
    
    # Average rating
    avg_rating = WorkerProfile.objects.filter(
        verification_status='verified'
    ).aggregate(Avg('average_rating'))['average_rating__avg'] or 0
    
    stats = {
        'total_users': total_users,
        'users_growth': abs(users_growth),
        'active_workers': active_workers,
        'workers_growth': abs(workers_growth),
        'total_jobs': total_jobs,
        'jobs_growth': abs(jobs_growth),
        'completed_jobs': completed,
        'completed_growth': abs(completed_growth),
        'verified_workers': verified_workers,
        'pending_workers': pending_workers,
        'available_workers': available_workers,
        'avg_rating': round(avg_rating, 1),
        'open_jobs': open_jobs,
        'in_progress_jobs': in_progress_jobs,
        'assigned_jobs': assigned_jobs,
    }
    
    context = {
        'days': days,
        'view_type': view_type,
        'new_workers': new_workers,
        'new_clients': new_clients,
        'new_jobs': new_jobs,
        'top_categories': top_categories,
        'top_workers': top_workers,
        'completion_rate': completion_rate,
        'chart_data_json': json.dumps(chart_data),
        'stats': stats,
        'recent_users': recent_users,
    }
    
    return render(request, 'admin_panel/reports.html', context)


@staff_member_required
def manage_users(request):
    """Manage all users in the system"""
    
    # Get filter parameters
    user_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    search = request.GET.get('search', '')
    
    # Base queryset
    users = User.objects.all().order_by('-date_joined')
    
    # Apply filters
    if user_type == 'worker':
        users = users.filter(user_type='worker')
    elif user_type == 'client':
        users = users.filter(user_type='client')
    elif user_type == 'admin':
        users = users.filter(Q(user_type='admin') | Q(is_staff=True))
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    # Search
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    # Get statistics for each user
    users_data = []
    for user in users:
        user_info = {
            'user': user,
            'jobs_posted': 0,
            'applications': 0,
            'ratings_given': 0,
            'ratings_received': 0,
            'avg_rating': 0,
        }
        
        if user.is_client:
            user_info['jobs_posted'] = JobRequest.objects.filter(client=user).count()
            user_info['ratings_given'] = Rating.objects.filter(client=user).count()
        
        if user.is_worker and hasattr(user, 'worker_profile'):
            user_info['applications'] = JobRequest.objects.filter(assigned_worker=user.worker_profile).count()
            ratings = Rating.objects.filter(worker=user.worker_profile)
            user_info['ratings_received'] = ratings.count()
            if ratings.exists():
                user_info['avg_rating'] = round(ratings.aggregate(Avg('rating'))['rating__avg'], 1)
        
        users_data.append(user_info)
    
    # Pagination
    paginator = Paginator(users_data, 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    # Overall statistics
    total_users = User.objects.count()
    total_workers = User.objects.filter(user_type='worker').count()
    total_clients = User.objects.filter(user_type='client').count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    
    context = {
        'users_page': users_page,
        'total_users': total_users,
        'total_workers': total_workers,
        'total_clients': total_clients,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'current_type': user_type,
        'current_status': status,
        'search': search,
    }
    
    return render(request, 'admin_panel/manage_users.html', context)


@staff_member_required
def user_detail(request, user_id):
    """View detailed information about a specific user"""
    
    user = get_object_or_404(User, pk=user_id)
    
    # Basic user info
    context = {
        'user': user,
        'jobs_posted': [],
        'applications': [],
        'ratings_given': [],
        'ratings_received': [],
        'messages_sent': 0,
        'messages_received': 0,
    }
    
    # Client specific data
    if user.is_client:
        jobs = JobRequest.objects.filter(client=user).order_by('-created_at')
        context['jobs_posted'] = jobs
        context['ratings_given'] = Rating.objects.filter(client=user).order_by('-created_at')
    
    # Worker specific data
    if user.is_worker and hasattr(user, 'worker_profile'):
        worker = user.worker_profile
        context['worker_profile'] = worker
        context['applications'] = JobRequest.objects.filter(assigned_worker=worker).order_by('-created_at')
        context['ratings_received'] = Rating.objects.filter(worker=worker).order_by('-created_at')
        context['documents'] = WorkerDocument.objects.filter(worker=worker)
        context['skills'] = worker.skills.all()
        
        # Calculate average rating
        ratings = Rating.objects.filter(worker=worker)
        if ratings.exists():
            context['avg_rating'] = round(ratings.aggregate(Avg('rating'))['rating__avg'], 1)
            context['total_ratings'] = ratings.count()
        else:
            context['avg_rating'] = 0
            context['total_ratings'] = 0
    
    # Messages
    context['messages_sent'] = Message.objects.filter(sender=user).count()
    context['messages_received'] = Message.objects.filter(recipient=user).count()
    
    # Activity timeline (last 10 activities)
    activities = []
    
    # Add job activities
    for job in JobRequest.objects.filter(client=user).order_by('-created_at')[:5]:
        activities.append({
            'type': 'job_posted',
            'date': job.created_at,
            'description': f'Posted job: {job.title}',
            'icon': 'briefcase'
        })
    
    # Add assignment activities
    if user.is_worker and hasattr(user, 'worker_profile'):
        for job in JobRequest.objects.filter(assigned_worker=user.worker_profile).order_by('-created_at')[:5]:
            activities.append({
                'type': 'assignment',
                'date': job.updated_at,
                'description': f'Assigned to job: {job.title}',
                'icon': 'check-circle'
            })
    
    # Sort activities by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    context['activities'] = activities[:10]
    
    return render(request, 'admin_panel/user_detail.html', context)


@staff_member_required
def toggle_user_status(request, user_id):
    """Activate or deactivate a user"""
    
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        
        # Don't allow deactivating self
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('admin_panel:user_detail', user_id=user_id)
        
        user.is_active = not user.is_active
        user.save()
        
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.email} has been {status}.')
        
        return redirect('admin_panel:user_detail', user_id=user_id)
    
    return redirect('admin_panel:manage_users')


@staff_member_required
def create_user(request):
    """Create a new user"""
    from django.contrib.auth.hashers import make_password
    
    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        user_type = request.POST.get('user_type')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return redirect('admin_panel:manage_users')
        
        try:
            # Create user
            user = User.objects.create(
                email=email,
                username=email,  # Use email as username
                password=make_password(password),
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                user_type=user_type,
                is_active=is_active
            )
            
            # Create related profile based on user type
            if user_type == 'worker':
                WorkerProfile.objects.create(user=user)
            elif user_type == 'client':
                ClientProfile.objects.create(user=user)
            
            messages.success(request, f'User {user.get_full_name()} has been created successfully.')
            return redirect('admin_panel:manage_users')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('admin_panel:manage_users')
    
    return redirect('admin_panel:manage_users')


@staff_member_required
def edit_user(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password')
        
        # Check if email is already taken by another user
        if User.objects.filter(email=email).exclude(pk=user_id).exists():
            messages.error(request, 'This email is already taken by another user.')
            return redirect('admin_panel:manage_users')
        
        try:
            # Update user
            user.email = email
            user.username = email
            user.first_name = first_name
            user.last_name = last_name
            user.phone_number = phone_number
            user.is_active = is_active
            
            # Update password if provided
            if password:
                from django.contrib.auth.hashers import make_password
                user.password = make_password(password)
            
            user.save()
            
            messages.success(request, f'User {user.get_full_name()} has been updated successfully.')
            return redirect('admin_panel:manage_users')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return redirect('admin_panel:manage_users')
    
    return redirect('admin_panel:manage_users')


@staff_member_required
def delete_user(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # Don't allow deleting self
        if user == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin_panel:user_detail', user_id=user_id)
        
        user_email = user.email
        user.delete()
        
        messages.success(request, f'User {user_email} has been deleted successfully.')
        return redirect('admin_panel:manage_users')
    
    return redirect('admin_panel:user_detail', user_id=user_id)


@staff_member_required
def system_overview(request):
    """Comprehensive system overview with all metrics"""
    
    # Time periods
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User metrics
    total_users = User.objects.count()
    new_users_today = User.objects.filter(date_joined__date=today).count()
    new_users_week = User.objects.filter(date_joined__date__gte=week_ago).count()
    new_users_month = User.objects.filter(date_joined__date__gte=month_ago).count()
    
    # Worker metrics
    total_workers = WorkerProfile.objects.count()
    verified_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    available_workers = WorkerProfile.objects.filter(availability='available', verification_status='verified').count()
    pending_verification = WorkerProfile.objects.filter(verification_status='pending').count()
    
    # Client metrics
    total_clients = ClientProfile.objects.count()
    active_clients = User.objects.filter(user_type='client', job_requests__isnull=False).distinct().count()
    
    # Job metrics
    total_jobs = JobRequest.objects.count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    in_progress_jobs = JobRequest.objects.filter(status='in_progress').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    cancelled_jobs = JobRequest.objects.filter(status='cancelled').count()
    
    jobs_today = JobRequest.objects.filter(created_at__date=today).count()
    jobs_week = JobRequest.objects.filter(created_at__date__gte=week_ago).count()
    jobs_month = JobRequest.objects.filter(created_at__date__gte=month_ago).count()
    
    # Application metrics
    pending_applications = JobRequest.objects.filter(status='open', assigned_worker__isnull=True).count()
    accepted_applications = JobRequest.objects.filter(assigned_worker__isnull=False).count()
    
    # Rating metrics
    total_ratings = Rating.objects.count()
    avg_rating = Rating.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    ratings_week = Rating.objects.filter(created_at__date__gte=week_ago).count()
    
    # Financial metrics (if budget field exists)
    total_budget = JobRequest.objects.aggregate(Sum('budget'))['budget__sum'] or 0
    completed_budget = JobRequest.objects.filter(status='completed').aggregate(Sum('budget'))['budget__sum'] or 0
    
    # Document metrics
    total_documents = WorkerDocument.objects.count()
    pending_documents = WorkerDocument.objects.filter(verification_status='pending').count()
    approved_documents = WorkerDocument.objects.filter(verification_status='approved').count()
    rejected_documents = WorkerDocument.objects.filter(verification_status='rejected').count()
    
    # Message metrics
    total_messages = Message.objects.count()
    messages_today = Message.objects.filter(created_at__date=today).count()
    
    # Category metrics
    total_categories = Category.objects.count()
    most_popular_categories = Category.objects.annotate(
        job_count=Count('jobs')
    ).order_by('-job_count')[:5]
    
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_jobs = JobRequest.objects.order_by('-created_at')[:5]
    recent_assignments = JobRequest.objects.filter(assigned_worker__isnull=False).order_by('-updated_at')[:5]
    
    context = {
        # User metrics
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        
        # Worker metrics
        'total_workers': total_workers,
        'verified_workers': verified_workers,
        'available_workers': available_workers,
        'pending_verification': pending_verification,
        
        # Client metrics
        'total_clients': total_clients,
        'active_clients': active_clients,
        
        # Job metrics
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        'cancelled_jobs': cancelled_jobs,
        'jobs_today': jobs_today,
        'jobs_week': jobs_week,
        'jobs_month': jobs_month,
        
        # Application metrics
        'pending_applications': pending_applications,
        'accepted_applications': accepted_applications,
        
        # Rating metrics
        'total_ratings': total_ratings,
        'avg_rating': round(avg_rating, 1),
        'ratings_week': ratings_week,
        
        # Financial metrics
        'total_budget': total_budget,
        'completed_budget': completed_budget,
        
        # Document metrics
        'total_documents': total_documents,
        'pending_documents': pending_documents,
        'approved_documents': approved_documents,
        'rejected_documents': rejected_documents,
        
        # Message metrics
        'total_messages': total_messages,
        'messages_today': messages_today,
        
        # Category metrics
        'total_categories': total_categories,
        'most_popular_categories': most_popular_categories,
        
        # Recent activities
        'recent_users': recent_users,
        'recent_jobs': recent_jobs,
        'recent_assignments': recent_assignments,
    }
    
    return render(request, 'admin_panel/system_overview.html', context)


@staff_member_required
def export_reports_csv(request):
    """Export reports to CSV format"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="worker_connect_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Worker Connect Platform Report'])
    writer.writerow([f'Report Period: Last {days} days'])
    writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])
    
    # User Statistics
    writer.writerow(['USER STATISTICS'])
    writer.writerow(['Metric', 'Count'])
    writer.writerow(['Total Users', User.objects.count()])
    writer.writerow(['Total Workers', User.objects.filter(user_type='worker').count()])
    writer.writerow(['Total Clients', User.objects.filter(user_type='client').count()])
    writer.writerow(['New Workers (Period)', WorkerProfile.objects.filter(created_at__gte=start_date).count()])
    writer.writerow(['New Clients (Period)', ClientProfile.objects.filter(created_at__gte=start_date).count()])
    writer.writerow([])
    
    # Worker Statistics
    writer.writerow(['WORKER STATISTICS'])
    writer.writerow(['Metric', 'Count'])
    writer.writerow(['Verified Workers', WorkerProfile.objects.filter(verification_status='verified').count()])
    writer.writerow(['Pending Verification', WorkerProfile.objects.filter(verification_status='pending').count()])
    writer.writerow(['Available Workers', WorkerProfile.objects.filter(availability='available').count()])
    avg_rating = WorkerProfile.objects.aggregate(Avg('average_rating'))['average_rating__avg'] or 0
    writer.writerow(['Average Rating', f'{avg_rating:.2f}'])
    writer.writerow([])
    
    # Job Statistics
    writer.writerow(['JOB STATISTICS'])
    writer.writerow(['Metric', 'Count'])
    writer.writerow(['Total Jobs', JobRequest.objects.count()])
    writer.writerow(['Jobs Posted (Period)', JobRequest.objects.filter(created_at__gte=start_date).count()])
    writer.writerow(['Open Jobs', JobRequest.objects.filter(status='open').count()])
    writer.writerow(['In Progress Jobs', JobRequest.objects.filter(status='in_progress').count()])
    writer.writerow(['Completed Jobs', JobRequest.objects.filter(status='completed').count()])
    writer.writerow(['Assigned Jobs', JobRequest.objects.filter(assigned_worker__isnull=False).count()])
    writer.writerow([])
    
    # Top Categories
    writer.writerow(['TOP CATEGORIES'])
    writer.writerow(['Category', 'Worker Count'])
    top_categories = Category.objects.annotate(
        worker_count=Count('workers')
    ).order_by('-worker_count')[:10]
    for category in top_categories:
        writer.writerow([category.name, category.worker_count])
    writer.writerow([])
    
    # Top Rated Workers
    writer.writerow(['TOP RATED WORKERS'])
    writer.writerow(['Name', 'Email', 'Rating', 'Completed Jobs'])
    top_workers = WorkerProfile.objects.filter(
        verification_status='verified'
    ).order_by('-average_rating')[:10]
    for worker in top_workers:
        writer.writerow([
            worker.user.get_full_name(),
            worker.user.email,
            f'{worker.average_rating:.2f}',
            worker.completed_jobs
        ])
    
    return response


@staff_member_required
def export_reports_excel(request):
    """Export reports to Excel format (using CSV with .xls extension)"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # For true Excel export, you would need openpyxl or xlsxwriter
    # For now, we'll use CSV with .xls extension (Excel can open it)
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="worker_connect_report_{timezone.now().strftime("%Y%m%d")}.xls"'
    
    writer = csv.writer(response, delimiter='\t')  # Tab-delimited for better Excel compatibility
    
    # Write header
    writer.writerow(['Worker Connect Platform Report'])
    writer.writerow([f'Report Period: Last {days} days'])
    writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])
    
    # Summary Statistics
    writer.writerow(['SUMMARY STATISTICS'])
    writer.writerow(['Category', 'Metric', 'Value'])
    
    total_users = User.objects.count()
    total_workers = User.objects.filter(user_type='worker').count()
    total_clients = User.objects.filter(user_type='client').count()
    new_workers = WorkerProfile.objects.filter(created_at__gte=start_date).count()
    new_clients = ClientProfile.objects.filter(created_at__gte=start_date).count()
    
    writer.writerow(['Users', 'Total Users', total_users])
    writer.writerow(['Users', 'Total Workers', total_workers])
    writer.writerow(['Users', 'Total Clients', total_clients])
    writer.writerow(['Users', f'New Workers ({days} days)', new_workers])
    writer.writerow(['Users', f'New Clients ({days} days)', new_clients])
    writer.writerow([])
    
    # Jobs
    total_jobs = JobRequest.objects.count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    
    writer.writerow(['Jobs', 'Total Jobs', total_jobs])
    writer.writerow(['Jobs', 'Open Jobs', open_jobs])
    writer.writerow(['Jobs', 'Completed Jobs', completed_jobs])
    writer.writerow([])
    
    # Recent Registrations Detail
    writer.writerow(['RECENT USER REGISTRATIONS'])
    writer.writerow(['Name', 'Email', 'User Type', 'Registration Date'])
    recent_users = User.objects.filter(date_joined__gte=start_date).order_by('-date_joined')
    for user in recent_users:
        writer.writerow([
            user.get_full_name(),
            user.email,
            user.get_user_type_display(),
            user.date_joined.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response


@staff_member_required
def export_reports_json(request):
    """Export reports to JSON format"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Gather all statistics
    data = {
        'report_info': {
            'title': 'Worker Connect Platform Report',
            'period_days': days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'user_statistics': {
            'total_users': User.objects.count(),
            'total_workers': User.objects.filter(user_type='worker').count(),
            'total_clients': User.objects.filter(user_type='client').count(),
            'new_workers': WorkerProfile.objects.filter(created_at__gte=start_date).count(),
            'new_clients': ClientProfile.objects.filter(created_at__gte=start_date).count()
        },
        'worker_statistics': {
            'verified_workers': WorkerProfile.objects.filter(verification_status='verified').count(),
            'pending_verification': WorkerProfile.objects.filter(verification_status='pending').count(),
            'available_workers': WorkerProfile.objects.filter(availability='available').count(),
            'average_rating': float(WorkerProfile.objects.aggregate(Avg('average_rating'))['average_rating__avg'] or 0)
        },
        'job_statistics': {
            'total_jobs': JobRequest.objects.count(),
            'jobs_in_period': JobRequest.objects.filter(created_at__gte=start_date).count(),
            'open_jobs': JobRequest.objects.filter(status='open').count(),
            'in_progress_jobs': JobRequest.objects.filter(status='in_progress').count(),
            'completed_jobs': JobRequest.objects.filter(status='completed').count(),
            'assigned_jobs': JobRequest.objects.filter(assigned_worker__isnull=False).count()
        },
        'top_categories': [],
        'top_workers': []
    }
    
    # Top categories
    top_categories = Category.objects.annotate(
        worker_count=Count('workers')
    ).order_by('-worker_count')[:10]
    
    for category in top_categories:
        data['top_categories'].append({
            'name': category.name,
            'worker_count': category.worker_count
        })
    
    # Top workers
    top_workers = WorkerProfile.objects.filter(
        verification_status='verified'
    ).order_by('-average_rating')[:10]
    
    for worker in top_workers:
        data['top_workers'].append({
            'name': worker.user.get_full_name(),
            'email': worker.user.email,
            'rating': float(worker.average_rating),
            'completed_jobs': worker.completed_jobs
        })
    
    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="worker_connect_report_{timezone.now().strftime("%Y%m%d")}.json"'
    
    return response


@staff_member_required
def export_reports_pdf(request):
    """Export reports to PDF format"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Create the HttpResponse object with PDF header
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="worker_connect_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Create the PDF object
    doc = SimpleDocTemplate(response, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0eb8a6'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0f766e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Add title
    elements.append(Paragraph("Worker Connect Platform Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Add report info
    report_info = f"Report Period: Last {days} days | Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elements.append(Paragraph(report_info, styles['Center']))
    elements.append(Spacer(1, 20))
    
    # Gather statistics
    total_users = User.objects.count()
    total_workers = User.objects.filter(user_type='worker').count()
    total_clients = User.objects.filter(user_type='client').count()
    new_workers = WorkerProfile.objects.filter(created_at__gte=start_date).count()
    new_clients = ClientProfile.objects.filter(created_at__gte=start_date).count()
    
    # User Statistics Table
    elements.append(Paragraph("User Statistics", heading_style))
    user_data = [
        ['Metric', 'Count'],
        ['Total Users', str(total_users)],
        ['Total Workers', str(total_workers)],
        ['Total Clients', str(total_clients)],
        [f'New Workers ({days} days)', str(new_workers)],
        [f'New Clients ({days} days)', str(new_clients)],
    ]
    
    user_table = Table(user_data, colWidths=[4*inch, 2*inch])
    user_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0eb8a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(user_table)
    elements.append(Spacer(1, 20))
    
    # Worker Statistics
    verified_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    pending_workers = WorkerProfile.objects.filter(verification_status='pending').count()
    available_workers = WorkerProfile.objects.filter(availability='available').count()
    avg_rating = WorkerProfile.objects.aggregate(Avg('average_rating'))['average_rating__avg'] or 0
    
    elements.append(Paragraph("Worker Statistics", heading_style))
    worker_data = [
        ['Metric', 'Count'],
        ['Verified Workers', str(verified_workers)],
        ['Pending Verification', str(pending_workers)],
        ['Available Workers', str(available_workers)],
        ['Average Rating', f'{avg_rating:.2f}'],
    ]
    
    worker_table = Table(worker_data, colWidths=[4*inch, 2*inch])
    worker_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(worker_table)
    elements.append(Spacer(1, 20))
    
    # Job Statistics
    total_jobs = JobRequest.objects.count()
    jobs_in_period = JobRequest.objects.filter(created_at__gte=start_date).count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    in_progress_jobs = JobRequest.objects.filter(status='in_progress').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    
    elements.append(Paragraph("Job Statistics", heading_style))
    job_data = [
        ['Metric', 'Count'],
        ['Total Jobs', str(total_jobs)],
        [f'Jobs Posted ({days} days)', str(jobs_in_period)],
        ['Open Jobs', str(open_jobs)],
        ['In Progress Jobs', str(in_progress_jobs)],
        ['Completed Jobs', str(completed_jobs)],
    ]
    
    job_table = Table(job_data, colWidths=[4*inch, 2*inch])
    job_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(job_table)
    elements.append(Spacer(1, 20))
    
    # Top Categories
    elements.append(Paragraph("Top Categories", heading_style))
    top_categories = Category.objects.annotate(
        worker_count=Count('workers')
    ).order_by('-worker_count')[:10]
    
    category_data = [['Category', 'Worker Count']]
    for category in top_categories:
        category_data.append([category.name, str(category.worker_count)])
    
    if len(category_data) > 1:
        category_table = Table(category_data, colWidths=[4*inch, 2*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        elements.append(category_table)
    else:
        elements.append(Paragraph("No category data available", styles['Normal']))
    
    elements.append(PageBreak())
    
    # Top Rated Workers
    elements.append(Paragraph("Top Rated Workers", heading_style))
    top_workers = WorkerProfile.objects.filter(
        verification_status='verified'
    ).order_by('-average_rating')[:10]
    
    worker_list_data = [['Name', 'Email', 'Rating', 'Completed Jobs']]
    for worker in top_workers:
        worker_list_data.append([
            worker.user.get_full_name(),
            worker.user.email,
            f'{worker.average_rating:.2f}',
            str(worker.completed_jobs)
        ])
    
    if len(worker_list_data) > 1:
        workers_table = Table(worker_list_data, colWidths=[2*inch, 2.5*inch, 0.8*inch, 1.2*inch])
        workers_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(workers_table)
    else:
        elements.append(Paragraph("No worker data available", styles['Normal']))
    
    # Add footer
    elements.append(Spacer(1, 30))
    footer_text = "This is an automated report generated by Worker Connect Platform"
    elements.append(Paragraph(footer_text, styles['Center']))
    
    # Build PDF
    doc.build(elements)
    
    return response


@staff_member_required
def job_management(request):
    """Manage jobs and assign workers"""
    
    # Get filter parameters
    status = request.GET.get('status', 'all')
    category_id = request.GET.get('category', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    jobs = JobRequest.objects.select_related(
        'client', 'category', 'assigned_worker'
    ).prefetch_related(
        'assigned_worker__user'
    ).order_by('-created_at')
    
    # Apply filters
    if status != 'all':
        jobs = jobs.filter(status=status)
    
    if category_id:
        jobs = jobs.filter(category_id=category_id)
    
    # Search
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page = request.GET.get('page', 1)
    jobs_page = paginator.get_page(page)
    
    # Statistics
    total_jobs = JobRequest.objects.count()
    open_jobs = JobRequest.objects.filter(status='open').count()
    assigned_jobs = JobRequest.objects.filter(assigned_worker__isnull=False, status='in_progress').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    
    # Get all categories for filter
    categories = Category.objects.all().order_by('name')
    
    # Get verified available workers for quick assignment
    available_workers = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).select_related('user').order_by('user__first_name')[:50]
    
    context = {
        'jobs_page': jobs_page,
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'assigned_jobs': assigned_jobs,
        'completed_jobs': completed_jobs,
        'categories': categories,
        'available_workers': available_workers,
        'current_status': status,
        'current_category': category_id,
        'search': search,
    }
    
    return render(request, 'admin_panel/job_management.html', context)


@staff_member_required
def assign_worker(request, job_id):
    """Assign a worker to a job"""
    
    job = get_object_or_404(JobRequest, pk=job_id)
    
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        action = request.POST.get('action')
        
        if action == 'assign':
            if not worker_id or worker_id == 'undefined' or worker_id == '':
                messages.error(request, 'Please select a worker first.')
                return redirect('admin_panel:assign_worker', job_id=job.id)
            # Validate worker_id is a valid number
            try:
                worker_id = int(worker_id)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid worker selection. Please try again.')
                return redirect('admin_panel:assign_worker', job_id=job.id)
            
            worker = get_object_or_404(WorkerProfile, pk=worker_id)
            
            # Check if worker is already assigned to this job
            if job.assigned_workers.filter(id=worker.id).exists():
                messages.warning(request, f'{worker.user.get_full_name()} is already assigned to this job.')
                return redirect('admin_panel:job_management')
            
            # Check if worker is busy (assigned to other jobs)
            if worker.availability == 'busy':
                messages.warning(request, f'{worker.user.get_full_name()} is currently assigned to another job.')
                return redirect('admin_panel:assign_worker', job_id=job.id)
            
            # Check if job is already fully staffed
            if job.is_fully_staffed:
                messages.warning(request, f'Job "{job.title}" is already fully staffed.')
                return redirect('admin_panel:job_management')
            
            # Assign worker to job (use new many-to-many field)
            job.assigned_workers.add(worker)
            job.status = 'in_progress'
            job.save()
            
            # Change worker availability to busy
            worker.availability = 'busy'
            worker.save()
            
            # Send notification message to both client and worker
            admin_user = request.user
            
            # Message to client with clickable links
            client_message = f"""We have assigned <a href="/clients/worker/{worker.id}/" style="color: #0f766e; text-decoration: none; font-weight: 600;">{worker.user.get_full_name()}</a> to your job '<a href="/jobs/{job.id}/" style="color: #0f766e; text-decoration: none; font-weight: 600;">{job.title}</a>'. The worker will start working on your project soon."""
            
            Message.objects.create(
                sender=admin_user,
                recipient=job.client,
                job=job,
                subject=f"Worker Assigned to Your Job: {job.title}",
                message=client_message
            )
            
            # Message to worker with clickable links  
            worker_message = f"""You have been assigned to the job '<a href="/jobs/{job.id}/" style="color: #0f766e; text-decoration: none; font-weight: 600;">{job.title}</a>' posted by <strong>{job.client.get_full_name()}</strong>. Please contact the client through admin to discuss the details."""
            
            Message.objects.create(
                sender=admin_user,
                recipient=worker.user,
                job=job,
                subject=f"You Have Been Assigned to a Job: {job.title}",
                message=worker_message
            )
            
            messages.success(request, f'Successfully assigned {worker.user.get_full_name()} to job: {job.title}')
            
        elif action == 'unassign':
            # Unassign worker (get worker_id for unassignment)
            worker_id = request.POST.get('worker_id')
            if worker_id:
                worker = get_object_or_404(WorkerProfile, pk=worker_id)
                worker_name = worker.user.get_full_name()
                
                # Remove worker from assigned workers
                job.assigned_workers.remove(worker)
                
                # Change worker availability back to available
                worker.availability = 'available'
                worker.save()
                
                # If no workers left, change job status back to open
                if not job.assigned_workers.exists():
                    job.status = 'open'
                job.save()
                
                messages.info(request, f'Unassigned {worker_name} from job: {job.title}')
            else:
                messages.error(request, 'No worker specified for unassignment')
        
        return redirect('admin_panel:job_management')
    
    # GET request - show assignment form
    # Get verified workers matching job category (only available workers)
    if job.category:
        suggested_workers = WorkerProfile.objects.filter(
            verification_status='verified',
            categories=job.category,
            availability='available'
        ).select_related('user').order_by('-average_rating')[:10]
    else:
        suggested_workers = []
    
    # Get all verified available workers (only truly available ones)
    all_workers = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).select_related('user').order_by('user__first_name')
    
    context = {
        'job': job,
        'suggested_workers': suggested_workers,
        'all_workers': all_workers,
    }
    
    return render(request, 'admin_panel/assign_worker.html', context)
