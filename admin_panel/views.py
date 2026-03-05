from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from decimal import Decimal
import csv
import json

from accounts.models import User
from workers.models import WorkerProfile, WorkerDocument, Category, Skill
from clients.models import ClientProfile, Rating
from jobs.models import Message
from jobs.service_request_models import ServiceRequest


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
    
    # Job statistics (ServiceRequest = new system)
    total_jobs = ServiceRequest.objects.count()
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    completed_jobs = ServiceRequest.objects.filter(status='completed').count()
    
    # Recent activities
    recent_workers = WorkerProfile.objects.order_by('-created_at')[:5]
    recent_jobs = ServiceRequest.objects.select_related('category', 'client', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')[:5]
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
    """Verify a worker - Only ID document required for basic verification"""
    worker = get_object_or_404(WorkerProfile, pk=worker_id)
    
    # Check if worker has ID document
    has_id = worker.has_id_document
    id_approved = worker.documents.filter(document_type='id', verification_status='approved').exists()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action in ['verify', 'approve']:
            # Check if ID is uploaded and approved
            if not has_id:
                messages.error(request, f'Cannot verify {worker.user.get_full_name()} - ID document not uploaded.')
            elif not id_approved:
                messages.warning(request, f'Cannot verify {worker.user.get_full_name()} - ID document needs to be approved first.')
            else:
                worker.verification_status = 'verified'
                worker.save()
                messages.success(request, f'Worker {worker.user.get_full_name()} has been verified! (ID document approved - other documents are optional)')
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
    
    context = {
        'worker': worker,
        'has_id': has_id,
        'id_approved': id_approved,
    }
    return render(request, 'admin_panel/verify_worker.html', context)


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
    """Manage categories - View, Add, Edit, Delete"""
    
    # Handle POST requests (Add new category)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', '').strip()
            daily_rate = request.POST.get('daily_rate', '25.00')
            
            if name:
                try:
                    daily_rate_decimal = Decimal(daily_rate)
                except (ValueError, TypeError):
                    daily_rate_decimal = Decimal('25.00')
                    
                category, created = Category.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': description,
                        'icon': icon,
                        'is_active': True,
                        'daily_rate': daily_rate_decimal
                    }
                )
                if created:
                    messages.success(request, f'Category "{name}" created successfully with daily rate ${daily_rate_decimal}!')
                else:
                    messages.warning(request, f'Category "{name}" already exists.')
            else:
                messages.error(request, 'Category name is required.')
        
        elif action == 'edit':
            category_id = request.POST.get('category_id')
            if category_id:
                try:
                    category = Category.objects.get(pk=category_id)
                    category.name = request.POST.get('name', category.name)
                    category.description = request.POST.get('description', '')
                    category.icon = request.POST.get('icon', '')
                    
                    # Update daily rate
                    daily_rate = request.POST.get('daily_rate')
                    if daily_rate:
                        try:
                            category.daily_rate = Decimal(daily_rate)
                        except (ValueError, TypeError):
                            pass  # Keep existing rate if invalid
                    
                    category.save()
                    messages.success(request, f'Category "{category.name}" updated successfully!')
                except Category.DoesNotExist:
                    messages.error(request, 'Category not found.')
        
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            if category_id:
                try:
                    category = Category.objects.get(pk=category_id)
                    category_name = category.name
                    category.delete()
                    messages.success(request, f'Category "{category_name}" deleted successfully!')
                except Category.DoesNotExist:
                    messages.error(request, 'Category not found.')
        
        elif action == 'toggle_status':
            category_id = request.POST.get('category_id')
            if category_id:
                try:
                    category = Category.objects.get(pk=category_id)
                    category.is_active = not category.is_active
                    category.save()
                    status = 'activated' if category.is_active else 'deactivated'
                    messages.success(request, f'Category "{category.name}" {status}!')
                except Category.DoesNotExist:
                    messages.error(request, 'Category not found.')
        
        return redirect('admin_panel:category_list')
    
    # GET request - display categories
    categories = Category.objects.annotate(
        worker_count=Count('workers'),
        job_count=Count('jobs')
    ).order_by('name')
    
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
    new_jobs = ServiceRequest.objects.filter(created_at__gte=start_date).count()
    
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
    prev_jobs = ServiceRequest.objects.filter(
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
    total_jobs = ServiceRequest.objects.filter(created_at__gte=start_date).count()
    completed = ServiceRequest.objects.filter(
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
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    in_progress_jobs = ServiceRequest.objects.filter(status='in_progress').count()
    assigned_jobs = ServiceRequest.objects.filter(assigned_worker__isnull=False).count()
    
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
            user_info['jobs_posted'] = ServiceRequest.objects.filter(client=user).count()
            user_info['ratings_given'] = Rating.objects.filter(client=user).count()
        
        if user.is_worker and hasattr(user, 'worker_profile'):
            user_info['applications'] = ServiceRequest.objects.filter(assigned_worker=user.worker_profile).count()
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
        jobs = ServiceRequest.objects.filter(client=user).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
        context['jobs_posted'] = jobs
        context['ratings_given'] = Rating.objects.filter(client=user).order_by('-created_at')
    
    # Worker specific data
    if user.is_worker and hasattr(user, 'worker_profile'):
        worker = user.worker_profile
        context['worker_profile'] = worker
        context['applications'] = ServiceRequest.objects.filter(assigned_worker=worker).select_related('category', 'client').order_by('-created_at')
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
    for job in ServiceRequest.objects.filter(client=user).order_by('-created_at')[:5]:
        activities.append({
            'type': 'job_posted',
            'date': job.created_at,
            'description': f'Posted service request: {job.title}',
            'icon': 'briefcase'
        })
    
    # Add assignment activities
    if user.is_worker and hasattr(user, 'worker_profile'):
        for job in ServiceRequest.objects.filter(assigned_worker=user.worker_profile).order_by('-created_at')[:5]:
            activities.append({
                'type': 'assignment',
                'date': job.updated_at,
                'description': f'Assigned to service request: {job.title}',
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
    active_clients = User.objects.filter(user_type='client', service_requests__isnull=False).distinct().count()
    
    # Job metrics (ServiceRequest = new system)
    total_jobs = ServiceRequest.objects.count()
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    in_progress_jobs = ServiceRequest.objects.filter(status='in_progress').count()
    completed_jobs = ServiceRequest.objects.filter(status='completed').count()
    cancelled_jobs = ServiceRequest.objects.filter(status='cancelled').count()
    
    jobs_today = ServiceRequest.objects.filter(created_at__date=today).count()
    jobs_week = ServiceRequest.objects.filter(created_at__date__gte=week_ago).count()
    jobs_month = ServiceRequest.objects.filter(created_at__date__gte=month_ago).count()
    
    # Application metrics
    pending_applications = ServiceRequest.objects.filter(status='pending').count()
    accepted_applications = ServiceRequest.objects.filter(assigned_worker__isnull=False).count()
    
    # Rating metrics
    total_ratings = Rating.objects.count()
    avg_rating = Rating.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    ratings_week = Rating.objects.filter(created_at__date__gte=week_ago).count()
    
    # Financial metrics
    total_budget = ServiceRequest.objects.aggregate(total=Sum('total_price'))['total'] or 0
    completed_budget = ServiceRequest.objects.filter(status='completed').aggregate(total=Sum('total_price'))['total'] or 0
    
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
        job_count=Count('service_requests')
    ).order_by('-job_count')[:5]
    
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_jobs = ServiceRequest.objects.select_related('category', 'client', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')[:5]
    recent_assignments = ServiceRequest.objects.filter(assigned_worker__isnull=False).select_related('category', 'client', 'assigned_worker', 'assigned_worker__user').order_by('-updated_at')[:5]
    
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
    writer.writerow(['Total Jobs', ServiceRequest.objects.count()])
    writer.writerow(['Jobs Posted (Period)', ServiceRequest.objects.filter(created_at__gte=start_date).count()])
    writer.writerow(['Pending Jobs', ServiceRequest.objects.filter(status='pending').count()])
    writer.writerow(['In Progress Jobs', ServiceRequest.objects.filter(status='in_progress').count()])
    writer.writerow(['Completed Jobs', ServiceRequest.objects.filter(status='completed').count()])
    writer.writerow(['Assigned Jobs', ServiceRequest.objects.filter(assigned_worker__isnull=False).count()])
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
    total_jobs = ServiceRequest.objects.count()
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    completed_jobs = ServiceRequest.objects.filter(status='completed').count()
    
    writer.writerow(['Jobs', 'Total Jobs', total_jobs])
    writer.writerow(['Jobs', 'Pending Jobs', open_jobs])
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
            'total_jobs': ServiceRequest.objects.count(),
            'jobs_in_period': ServiceRequest.objects.filter(created_at__gte=start_date).count(),
            'pending_jobs': ServiceRequest.objects.filter(status='pending').count(),
            'in_progress_jobs': ServiceRequest.objects.filter(status='in_progress').count(),
            'completed_jobs': ServiceRequest.objects.filter(status='completed').count(),
            'assigned_jobs': ServiceRequest.objects.filter(assigned_worker__isnull=False).count()
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
    total_jobs = ServiceRequest.objects.count()
    jobs_in_period = ServiceRequest.objects.filter(created_at__gte=start_date).count()
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    in_progress_jobs = ServiceRequest.objects.filter(status='in_progress').count()
    completed_jobs = ServiceRequest.objects.filter(status='completed').count()
    
    elements.append(Paragraph("Job Statistics", heading_style))
    job_data = [
        ['Metric', 'Count'],
        ['Total Jobs', str(total_jobs)],
        [f'Jobs Posted ({days} days)', str(jobs_in_period)],
        ['Pending Jobs', str(open_jobs)],
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
    jobs = ServiceRequest.objects.select_related(
        'client', 'category', 'assigned_worker',
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
    total_jobs = ServiceRequest.objects.count()
    open_jobs = ServiceRequest.objects.filter(status='pending').count()
    assigned_jobs = ServiceRequest.objects.filter(assigned_worker__isnull=False, status='in_progress').count()
    completed_jobs = ServiceRequest.objects.filter(status='completed').count()
    
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


# Legacy function removed - use assign_worker_to_request() instead
# This function used JobRequest with M2M assigned_workers (deprecated)
# All functionality moved to assign_worker_to_request() which uses ServiceRequest with FK assigned_worker


@staff_member_required
def service_request_list(request):
    """List all service requests with filters"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    urgency_filter = request.GET.get('urgency', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    export_csv = request.GET.get('export', '')
    
    # Base queryset
    requests = ServiceRequest.objects.select_related(
        'client', 'category', 'assigned_worker', 'assigned_worker__user'
    ).order_by('-created_at')
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    if urgency_filter:
        requests = requests.filter(urgency=urgency_filter)
    if category_filter:
        requests = requests.filter(category_id=category_filter)
    if search_query:
        requests = requests.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(client__first_name__icontains=search_query) |
            Q(client__last_name__icontains=search_query)
        )
    
    # CSV Export
    if export_csv == 'yes':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="service_requests.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Title', 'Client', 'Category', 'Status', 'Urgency',
            'Location', 'City', 'Duration (hrs)', 'Hourly Rate', 'Total Amount',
            'Worker', 'Created', 'Assigned', 'Completed', 'Rating'
        ])
        
        for req in requests:
            writer.writerow([
                req.id,
                req.title,
                req.client.get_full_name(),
                req.category.name if req.category else '',
                req.get_status_display(),
                req.get_urgency_display(),
                req.location,
                req.city,
                req.estimated_duration_hours or 0,
                req.hourly_rate or 0,
                req.total_amount or 0,
                req.assigned_worker.user.get_full_name() if req.assigned_worker else 'Unassigned',
                req.created_at.strftime('%Y-%m-%d %H:%M'),
                req.assigned_at.strftime('%Y-%m-%d %H:%M') if req.assigned_at else '',
                req.work_completed_at.strftime('%Y-%m-%d %H:%M') if req.work_completed_at else '',
                req.client_rating or ''
            ])
        
        return response
    
    # Statistics
    stats = {
        'total': ServiceRequest.objects.count(),
        'pending': ServiceRequest.objects.filter(status='pending').count(),
        'assigned': ServiceRequest.objects.filter(status='assigned').count(),
        'in_progress': ServiceRequest.objects.filter(status='in_progress').count(),
        'completed': ServiceRequest.objects.filter(status='completed').count(),
        'urgent': ServiceRequest.objects.filter(urgency='urgent').count(),
        'emergency': ServiceRequest.objects.filter(urgency='emergency').count(),
    }
    
    # Pagination
    paginator = Paginator(requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'categories': categories,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'category_filter': category_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/service_request_list.html', context)


@staff_member_required
def service_request_detail(request, request_id):
    """View service request details"""
    
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related(
            'client', 'category', 'assigned_worker', 'assigned_worker__user', 'assigned_by'
        ),
        id=request_id
    )
    
    # Get time logs
    time_logs = service_request.time_logs.all().order_by('-clock_in')
    
    # Get available workers for this category
    if service_request.category:
        available_workers = WorkerProfile.objects.filter(
            categories=service_request.category,
            verification_status='verified'
        ).exclude(
            availability='offline'
        ).select_related('user').order_by('-average_rating')[:15]
    else:
        available_workers = WorkerProfile.objects.filter(
            verification_status='verified'
        ).exclude(
            availability='offline'
        ).select_related('user').order_by('-average_rating')[:15]
    
    context = {
        'service_request': service_request,
        'time_logs': time_logs,
        'available_workers': available_workers,
    }
    
    return render(request, 'admin_panel/service_request_detail.html', context)


@staff_member_required
def view_request_workers(request, request_id):
    """View all workers available for a service request"""
    
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related(
            'client', 'category', 'assigned_worker', 'assigned_worker__user'
        ),
        id=request_id
    )
    
    # Get all verified workers for this category (no limit)
    if service_request.category:
        available_workers = WorkerProfile.objects.filter(
            categories=service_request.category,
            verification_status='verified'
        ).select_related('user').prefetch_related('categories').order_by('-average_rating')
    else:
        # If no category, show all verified workers
        available_workers = WorkerProfile.objects.filter(
            verification_status='verified'
        ).select_related('user').prefetch_related('categories').order_by('-average_rating')
    
    context = {
        'service_request': service_request,
        'available_workers': available_workers,
        'workers_count': available_workers.count(),
    }
    
    return render(request, 'admin_panel/view_request_workers.html', context)


@staff_member_required
def assign_worker_to_request(request, request_id):
    """Assign a worker to a service request"""
    
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        admin_notes = request.POST.get('admin_notes', '')
        
        if not worker_id:
            messages.error(request, 'Please select a worker')
            return redirect('admin_panel:service_request_detail', request_id=request_id)
        
        try:
            worker = WorkerProfile.objects.get(id=worker_id)
            
            # Check if worker has the required category
            if service_request.category and not worker.categories.filter(id=service_request.category.id).exists():
                messages.warning(request, f'{worker.user.get_full_name()} does not have the required category')
            
            # Assign the worker
            service_request.assign_worker(worker, request.user, admin_notes)
            
            messages.success(
                request,
                f'Successfully assigned {worker.user.get_full_name()} to "{service_request.title}"'
            )
            
            # Notify worker (the assign_worker method already handles this)
            
        except WorkerProfile.DoesNotExist:
            messages.error(request, 'Worker not found')
        except Exception as e:
            messages.error(request, f'Error assigning worker: {str(e)}')
    
    return redirect('admin_panel:service_request_detail', request_id=request_id)


@staff_member_required
def rate_worker(request, worker_id):
    """Admin rate a worker"""
    from clients.models import Rating
    from django.db import models
    
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    
    # Get existing admin rating if exists
    existing_rating = Rating.objects.filter(
        client=request.user,
        worker=worker
    ).first()
    
    if request.method == 'POST':
        rating_value = request.POST.get('rating')
        review_text = request.POST.get('review', '').strip()
        
        if not rating_value:
            messages.error(request, 'Please select a rating')
            return render(request, 'admin_panel/rate_worker.html', {
                'worker': worker,
                'existing_rating': existing_rating
            })
        
        try:
            rating_value = int(rating_value)
            if rating_value < 1 or rating_value > 5:
                messages.error(request, 'Rating must be between 1 and 5 stars')
                return render(request, 'admin_panel/rate_worker.html', {
                    'worker': worker,
                    'existing_rating': existing_rating
                })
            
            if existing_rating:
                # Update existing rating
                existing_rating.rating = rating_value
                existing_rating.review = review_text
                existing_rating.save()
                messages.success(request, f'Successfully updated your rating for {worker.user.get_full_name()}')
            else:
                # Create new rating
                Rating.objects.create(
                    client=request.user,
                    worker=worker,
                    rating=rating_value,
                    review=review_text
                )
                messages.success(request, f'Successfully rated {worker.user.get_full_name()} with {rating_value} stars')
            
            # Update worker's average rating
            worker_ratings = Rating.objects.filter(worker=worker)
            if worker_ratings.exists():
                avg_rating = worker_ratings.aggregate(models.Avg('rating'))['rating__avg']
                worker.average_rating = round(avg_rating, 2)
                worker.save()
                
            # Redirect to worker ratings page to see the result
            return redirect('admin_panel:worker_ratings', worker_id=worker_id)
            
        except ValueError:
            messages.error(request, 'Invalid rating value')
        except Exception as e:
            messages.error(request, f'Error saving rating: {str(e)}')
    
    # GET request - show the rating form
    context = {
        'worker': worker,
        'existing_rating': existing_rating
    }
    return render(request, 'admin_panel/rate_worker.html', context)


@staff_member_required  
def worker_ratings(request, worker_id):
    """View all ratings for a specific worker"""
    from clients.models import Rating
    
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    ratings = Rating.objects.filter(worker=worker).select_related('client').order_by('-created_at')
    
    # Get rating statistics
    rating_stats = ratings.aggregate(
        total=models.Count('id'),
        average=models.Avg('rating'),
        five_star=models.Count('id', filter=models.Q(rating=5)),
        four_star=models.Count('id', filter=models.Q(rating=4)),
        three_star=models.Count('id', filter=models.Q(rating=3)),
        two_star=models.Count('id', filter=models.Q(rating=2)),
        one_star=models.Count('id', filter=models.Q(rating=1)),
    )
    
    # Calculate percentages for CSS width values
    total_ratings = rating_stats['total'] or 1  # Avoid division by zero
    rating_percentages = {
        'five_star_pct': (rating_stats['five_star'] / total_ratings) * 100,
        'four_star_pct': (rating_stats['four_star'] / total_ratings) * 100,
        'three_star_pct': (rating_stats['three_star'] / total_ratings) * 100,
        'two_star_pct': (rating_stats['two_star'] / total_ratings) * 100,
        'one_star_pct': (rating_stats['one_star'] / total_ratings) * 100,
    }
    
    context = {
        'worker': worker,
        'ratings': ratings,
        'rating_stats': rating_stats,
        'rating_percentages': rating_percentages,
    }
    
    return render(request, 'admin_panel/worker_ratings.html', context)
