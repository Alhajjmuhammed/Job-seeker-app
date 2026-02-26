from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from workers.models import WorkerProfile, Category
from .models import ClientProfile
from .forms import ClientProfileForm
from jobs.models import JobRequest


@login_required
def client_dashboard(request):
    """Client dashboard view"""
    if not request.user.is_client:
        messages.error(request, 'Access denied. Clients only.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    # Get available service categories with stats
    categories_with_stats = []
    for category in Category.objects.filter(is_active=True)[:8]:
        available_workers = WorkerProfile.objects.filter(
            categories=category,
            verification_status='verified',
            availability='available'
        ).count()
        
        completed_projects = JobRequest.objects.filter(
            category=category,
            status='completed'
        ).count()
        
        categories_with_stats.append({
            'category': category,
            'available_workers': available_workers,
            'completed_projects': completed_projects,
        })
    
    # Get recent service requests
    recent_requests = JobRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker').order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'categories_with_stats': categories_with_stats,
        'recent_requests': recent_requests,
    }
    return render(request, 'clients/dashboard.html', context)


@login_required
def browse_services(request):
    """Browse available service categories"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all active categories with statistics
    services = []
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    for category in categories:
        available_workers = WorkerProfile.objects.filter(
            categories=category,
            verification_status='verified',
            availability='available'
        ).count()
        
        completed_projects = JobRequest.objects.filter(
            category=category,
            status='completed'
        ).count()
        
        avg_completion_days = JobRequest.objects.filter(
            category=category,
            status='completed'
        ).aggregate(
            avg_days=Avg('completion_days')
        )['avg_days'] or 0
        
        services.append({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'available_workers': available_workers,
            'completed_projects': completed_projects,
            'avg_completion_days': int(avg_completion_days),
            'is_available': available_workers > 0,
        })
    
    context = {
        'services': services,
    }
    return render(request, 'clients/browse_services.html', context)


@login_required
def request_service(request, category_id):
    """Request a specific service"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    category = get_object_or_404(Category, id=category_id, is_active=True)
    
    if request.method == 'POST':
        # Create service request
        job_request = JobRequest.objects.create(
            client=request.user,
            category=category,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            budget=request.POST.get('budget'),
            location=request.POST.get('location'),
            urgency=request.POST.get('urgency', 'normal'),
            workers_needed=int(request.POST.get('workers_needed', 1)),
            status='pending'
        )
        
        messages.success(request, 
            f'Your {category.name} service request has been submitted! '
            'Our team will assign a qualified worker and notify you within 2-4 hours.'
        )
        return redirect('clients:service_request_detail', request_id=job_request.id)
    
    # Get service statistics
    available_workers = WorkerProfile.objects.filter(
        categories=category,
        verification_status='verified',
        availability='available'
    ).count()
    
    completed_projects = JobRequest.objects.filter(
        category=category,
        status='completed'
    ).count()
    
    context = {
        'category': category,
        'available_workers': available_workers,
        'completed_projects': completed_projects,
    }
    return render(request, 'clients/request_service.html', context)


@login_required
def my_service_requests(request):
    """View client's service requests"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    status_filter = request.GET.get('status', 'all')
    
    requests = JobRequest.objects.filter(client=request.user)
    
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    requests = requests.select_related(
        'category', 'assigned_worker'
    ).order_by('-created_at')
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'status_choices': [
            ('all', 'All Requests'),
            ('pending', 'Pending Assignment'),
            ('assigned', 'Worker Assigned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ]
    }
    return render(request, 'clients/my_service_requests.html', context)


@login_required
def service_request_detail(request, request_id):
    """View details of a service request"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    service_request = get_object_or_404(
        JobRequest, 
        id=request_id, 
        client=request.user
    )
    
    context = {
        'request': service_request,
    }
    return render(request, 'clients/service_request_detail.html', context)


@login_required
def profile_edit(request):
    """Edit client profile"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ClientProfileForm(request.POST, instance=profile)
        
        # Get phone number from POST data
        phone_number = request.POST.get('phone_number', '').strip()
        
        if form.is_valid():
            form.save()
            
            # Update user's phone number
            if phone_number:
                request.user.phone_number = phone_number
                request.user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('clients:profile')
    else:
        form = ClientProfileForm(instance=profile)
    
    return render(request, 'clients/profile_edit.html', {'form': form, 'profile': profile})


@login_required
def profile_view(request):
    """View client profile"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    # Get statistics
    total_requests = JobRequest.objects.filter(client=request.user).count()
    pending_requests = JobRequest.objects.filter(client=request.user, status='pending').count()
    in_progress_requests = JobRequest.objects.filter(client=request.user, status='in_progress').count()
    completed_requests = JobRequest.objects.filter(client=request.user, status='completed').count()
    
    # Recent service requests
    recent_requests = JobRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker').order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'recent_requests': recent_requests,
    }
    return render(request, 'clients/profile.html', context)


@login_required
def cancel_service_request(request, request_id):
    """Cancel a service request"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    if request.method == 'POST':
        service_request = get_object_or_404(
            JobRequest, 
            id=request_id, 
            client=request.user,
            status='pending'  # Only pending requests can be cancelled
        )
        
        service_request.status = 'cancelled'
        service_request.save()
        
        messages.success(request, 'Service request cancelled successfully.')
        return redirect('clients:my_service_requests')
    
    return redirect('clients:my_service_requests')
