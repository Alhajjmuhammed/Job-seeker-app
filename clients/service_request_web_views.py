"""
Web Views for Clients - Service Request System
Clients can use web browser to request services and view history
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum

from jobs.service_request_models import ServiceRequest
from workers.models import Category
from django.utils import timezone


@login_required
def client_web_dashboard(request):
    """Client web dashboard - overview of all service requests"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    # Get statistics
    total_requests = ServiceRequest.objects.filter(client=request.user).count()
    pending = ServiceRequest.objects.filter(client=request.user, status='pending').count()
    in_progress = ServiceRequest.objects.filter(
        client=request.user, 
        status__in=['assigned', 'in_progress']
    ).count()
    completed = ServiceRequest.objects.filter(client=request.user, status='completed').count()
    
    # Total spent
    total_spent = ServiceRequest.objects.filter(
        client=request.user,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Recent requests
    recent_requests = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')[:5]
    
    context = {
        'total_requests': total_requests,
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'total_spent': total_spent,
        'recent_requests': recent_requests,
        'active_menu': 'dashboard'
    }
    
    return render(request, 'service_requests/client/dashboard.html', context)


@login_required
def client_web_request_service(request):
    """Client creates a new service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            # Create service request
            service_request = ServiceRequest.objects.create(
                client=request.user,
                category_id=request.POST.get('category'),
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                location=request.POST.get('location'),
                city=request.POST.get('city'),
                preferred_date=request.POST.get('preferred_date') or None,
                preferred_time=request.POST.get('preferred_time') or None,
                estimated_duration_hours=request.POST.get('estimated_duration_hours'),
                urgency=request.POST.get('urgency', 'normal'),
                client_notes=request.POST.get('client_notes', ''),
                status='pending'
            )
            
            # Update client profile
            if hasattr(request.user, 'client_profile'):
                profile = request.user.client_profile
                profile.total_jobs_posted += 1
                profile.save()
            
            # Notify admin
            from worker_connect.notification_service import NotificationService
            NotificationService.notify_admin_new_service_request(service_request)
            
            messages.success(request, '✅ Service request created! Admin will assign a worker soon.')
            return redirect('service_requests_web:client_request_detail', pk=service_request.id)
            
        except Exception as e:
            messages.error(request, f'Error creating request: {str(e)}')
    
    context = {
        'categories': categories,
        'active_menu': 'request_service'
    }
    
    return render(request, 'service_requests/client/request_service.html', context)


@login_required
def client_web_my_requests(request):
    """List all service requests by this client"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    # Get all requests
    requests_list = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        requests_list = requests_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(requests_list, 10)
    page = request.GET.get('page', 1)
    service_requests = paginator.get_page(page)
    
    context = {
        'service_requests': service_requests,
        'status_filter': status_filter,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/my_requests.html', context)


@login_required
def client_web_request_detail(request, pk):
    """View detailed service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Get time logs
    time_logs = service_request.time_logs.all()
    
    context = {
        'service_request': service_request,
        'time_logs': time_logs,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/request_detail.html', context)


@login_required
def client_web_cancel_request(request, pk):
    """Cancel a service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    if service_request.status in ['in_progress', 'completed']:
        messages.error(request, f'Cannot cancel service that is {service_request.status}')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    if request.method == 'POST':
        service_request.status = 'cancelled'
        service_request.save()
        
        # Notify worker if assigned
        if service_request.assigned_worker:
            from worker_connect.notification_service import NotificationService
            NotificationService.notify_service_cancelled(service_request)
        
        messages.success(request, 'Service request cancelled.')
        return redirect('service_requests_web:client_my_requests')
    
    context = {
        'service_request': service_request
    }
    
    return render(request, 'service_requests/client/cancel_request.html', context)


@login_required
def client_web_history(request):
    """View completed service requests history"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    requests_list = ServiceRequest.objects.filter(
        client=request.user,
        status='completed'
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-work_completed_at')
    
    # Pagination
    paginator = Paginator(requests_list, 10)
    page = request.GET.get('page', 1)
    service_requests = paginator.get_page(page)
    
    # Calculate total spent
    total_spent = ServiceRequest.objects.filter(
        client=request.user,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'service_requests': service_requests,
        'total_spent': total_spent,
        'active_menu': 'history'
    }
    
    return render(request, 'service_requests/client/history.html', context)
