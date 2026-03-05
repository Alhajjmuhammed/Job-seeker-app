from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from workers.models import WorkerProfile, Category
from .models import ClientProfile
from .forms import ClientProfileForm
from jobs.service_request_models import ServiceRequest


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
        
        completed_projects = ServiceRequest.objects.filter(
            category=category,
            status='completed'
        ).count()
        
        categories_with_stats.append({
            'category': category,
            'available_workers': available_workers,
            'completed_projects': completed_projects,
        })
    
    # Get recent service requests
    recent_requests = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')[:5]
    
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
        
        completed_projects = ServiceRequest.objects.filter(
            category=category,
            status='completed'
        ).count()
        
        avg_completion_days = ServiceRequest.objects.filter(
            category=category,
            status='completed'
        ).aggregate(
            avg_days=Avg('duration_days')
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
        try:
            # Get form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            location = request.POST.get('location', '').strip()
            city = request.POST.get('city', '').strip()
            duration_type = request.POST.get('duration_type')
            urgency = request.POST.get('urgency', 'normal')
            client_notes = request.POST.get('client_notes', '').strip()
            
            # Parse dates
            preferred_date = request.POST.get('preferred_date')
            preferred_time = request.POST.get('preferred_time')
            service_start_date = request.POST.get('service_start_date')
            service_end_date = request.POST.get('service_end_date')
            
            # Calculate duration and pricing
            daily_rate = float(category.daily_rate)  # Use category-specific daily rate
            duration_days = 1
            
            if duration_type == 'daily':
                duration_days = 1
            elif duration_type == 'monthly':
                duration_days = 30
            elif duration_type == '3_months':
                duration_days = 90
            elif duration_type == '6_months':
                duration_days = 180
            elif duration_type == 'yearly':
                duration_days = 365
            elif duration_type == 'custom' and service_start_date and service_end_date:
                start_date = datetime.strptime(service_start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(service_end_date, '%Y-%m-%d').date()
                duration_days = (end_date - start_date).days + 1
            
            total_price = duration_days * daily_rate
            
            # Create service request
            service_request = ServiceRequest.objects.create(
                client=request.user,
                category=category,
                title=title,
                description=description,
                location=location,
                city=city,
                urgency=urgency,
                duration_type=duration_type,
                duration_days=duration_days,
                daily_rate=daily_rate,
                total_price=total_price,
                preferred_date=preferred_date if preferred_date else None,
                preferred_time=preferred_time if preferred_time else None,
                service_start_date=service_start_date if service_start_date else None,
                service_end_date=service_end_date if service_end_date else None,
                client_notes=client_notes if client_notes else None,
                status='pending',
                payment_status='pending'
            )
            
            messages.success(request, 
                f'Your {category.name} service request has been submitted! '
                f'Total price: SDG {total_price:.2f}. '
                'Our team will assign a qualified worker and notify you within 2-4 hours.'
            )
            return redirect('service_requests_web:client_request_detail', pk=service_request.id)
            
        except Exception as e:
            messages.error(request, f'Error creating service request: {str(e)}')
    
    # Get service statistics
    available_workers = WorkerProfile.objects.filter(
        categories=category,
        verification_status='verified',
        availability='available'
    ).count()
    
    completed_projects = ServiceRequest.objects.filter(
        category=category,
        status='completed'
    ).count()
    
    context = {
        'category': category,
        'available_workers': available_workers,
        'completed_projects': completed_projects,
        'daily_rate': category.daily_rate,
    }
    return render(request, 'clients/request_service.html', context)


@login_required
def my_service_requests(request):
    """View client's service requests"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    status_filter = request.GET.get('status', 'all')
    
    requests = ServiceRequest.objects.filter(client=request.user)
    
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    requests = requests.select_related(
        'category', 'assigned_worker', 'assigned_worker__user'
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
        ServiceRequest, 
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
    total_requests = ServiceRequest.objects.filter(client=request.user).count()
    pending_requests = ServiceRequest.objects.filter(client=request.user, status='pending').count()
    in_progress_requests = ServiceRequest.objects.filter(client=request.user, status='in_progress').count()
    completed_requests = ServiceRequest.objects.filter(client=request.user, status='completed').count()
    
    # Recent service requests
    recent_requests = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')[:5]
    
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
            ServiceRequest, 
            id=request_id, 
            client=request.user,
            status='pending'  # Only pending requests can be cancelled
        )
        
        service_request.status = 'cancelled'
        service_request.save()
        
        messages.success(request, 'Service request cancelled successfully.')
        return redirect('clients:my_service_requests')
    
    return redirect('clients:my_service_requests')
