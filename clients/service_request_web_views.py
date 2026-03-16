"""
Web Views for Clients - Service Request System
Clients can use web browser to request services and view history
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from jobs.service_request_models import ServiceRequest, WorkerActivity
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
    """Client creates a new service request - matching the working template exactly"""
    from datetime import datetime
    
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            # Get category
            category_id = request.POST.get('category')
            category = Category.objects.get(id=category_id, is_active=True)
            
            # Get workers_needed from POST or default to 1
            workers_needed = request.POST.get('workers_needed', '1')
            try:
                workers_needed = int(workers_needed)
                workers_needed = max(1, min(100, workers_needed))  # Clamp between 1 and 100
            except (ValueError, TypeError):
                workers_needed = 1
            
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
            
            # Calculate total: daily_rate × duration_days × workers_needed
            total_price = duration_days * daily_rate * workers_needed
            
            # Get payment data
            payment_method = request.POST.get('payment_method', 'pending')
            payment_transaction_id = request.POST.get('payment_transaction_id', '')
            payment_screenshot = request.FILES.get('payment_screenshot')
            
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
                workers_needed=workers_needed,
                status='pending',
                payment_status='pending',
                payment_method=payment_method,
                payment_transaction_id=payment_transaction_id
            )
            
            # Save payment screenshot if provided
            if payment_screenshot:
                service_request.payment_screenshot = payment_screenshot
                service_request.save()
            
            # Update client profile
            if hasattr(request.user, 'client_profile'):
                profile = request.user.client_profile
                profile.total_jobs_posted += 1
                profile.save()
            
            # Notify admin
            from worker_connect.notification_service import NotificationService
            NotificationService.notify_admin_new_service_request(service_request)
            
            # Success message
            messages.success(request, 
                f'Your {category.name} service request has been submitted! '
                f'Total price: TSH {total_price:.2f}. '
                'Our team will assign a qualified worker and notify you within 2-4 hours.'
            )
            return redirect('service_requests_web:client_request_detail', pk=service_request.id)
            
        except Exception as e:
            messages.error(request, f'Error creating service request: {str(e)}')
    
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
    
    # Get all categories
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    # Get all requests
    requests_list = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    search_query = request.GET.get('search', '').strip()
    
    # Apply filters
    if status_filter:
        requests_list = requests_list.filter(status=status_filter)
    if category_filter:
        requests_list = requests_list.filter(category_id=category_filter)
    if from_date:
        requests_list = requests_list.filter(created_at__gte=from_date)
    if to_date:
        requests_list = requests_list.filter(created_at__lte=to_date)
    if search_query:
        requests_list = requests_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Get counts for quick status buttons
    all_requests = ServiceRequest.objects.filter(client=request.user)
    total_count = all_requests.count()
    pending_count = all_requests.filter(status='pending').count()
    assigned_count = all_requests.filter(status='assigned').count()
    in_progress_count = all_requests.filter(status='in_progress').count()
    completed_count = all_requests.filter(status='completed').count()
    
    # Pagination
    paginator = Paginator(requests_list, 12)
    page = request.GET.get('page', 1)
    requests_paginated = paginator.get_page(page)
    
    context = {
        'requests': requests_paginated,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'from_date': from_date,
        'to_date': to_date,
        'search_query': search_query,
        'total_count': total_count,
        'pending_count': pending_count,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
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
    time_logs = service_request.time_logs.all().order_by('-clock_in')
    
    # Get worker assignments - only show accepted/in_progress/completed workers
    # Clients should only see workers who have accepted their request (not pending or rejected)
    assignments = service_request.assignments.filter(
        status__in=['accepted', 'in_progress', 'completed']
    ).select_related('worker', 'worker__user').order_by('assignment_number')
    
    context = {
        'service_request': service_request,
        'time_logs': time_logs,
        'assignments': assignments,
        'assignments_count': assignments.count(),
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
    
    # Check if request can be cancelled
    if service_request.status in ['completed', 'cancelled']:
        messages.error(request, f'Cannot cancel request that is already {service_request.status}.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    if request.method == 'POST':
        # Get cancellation details
        cancellation_reason_type = request.POST.get('cancellation_reason_type')
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        
        if not cancellation_reason or len(cancellation_reason) < 10:
            messages.error(request, 'Please provide a detailed reason for cancellation (at least 10 characters).')
            context = {'service_request': service_request}
            return render(request, 'service_requests/client/cancel_confirm.html', context)
        
        # Update request
        service_request.status = 'cancelled'
        service_request.cancelled_at = timezone.now()
        service_request.cancellation_reason = f"[{cancellation_reason_type}] {cancellation_reason}"
        service_request.save()
        
        # Notify worker if assigned
        if service_request.assigned_worker:
            try:
                from worker_connect.notification_service import NotificationService
                NotificationService.notify_service_cancelled(service_request)
            except Exception as e:
                # Don't fail cancellation if notification fails
                print(f"Failed to send cancellation notification: {e}")
        
        messages.success(request, '✅ Service request has been cancelled.')
        return redirect('service_requests_web:client_my_requests')
    
    context = {
        'service_request': service_request,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/cancel_confirm.html', context)


@login_required
def client_web_edit_request(request, pk):
    """Edit a pending service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Check if request can be edited (only pending requests)
    if service_request.status != 'pending':
        messages.error(request, f'Cannot edit request that is {service_request.status}. Only pending requests can be edited.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            # Update service request fields
            service_request.title = request.POST.get('title', '').strip()
            service_request.description = request.POST.get('description', '').strip()
            service_request.location = request.POST.get('location', '').strip()
            service_request.city = request.POST.get('city', '').strip()
            service_request.preferred_date = request.POST.get('preferred_date') or None
            service_request.preferred_time = request.POST.get('preferred_time') or None
            service_request.estimated_duration_hours = request.POST.get('estimated_duration_hours')
            service_request.urgency = request.POST.get('urgency', 'normal')
            service_request.client_notes = request.POST.get('client_notes', '').strip()
            
            # Validate required fields
            if not service_request.title:
                messages.error(request, 'Title is required.')
                raise ValueError('Title is required')
            if not service_request.description or len(service_request.description) < 20:
                messages.error(request, 'Description must be at least 20 characters.')
                raise ValueError('Description too short')
            if not service_request.location:
                messages.error(request, 'Location is required.')
                raise ValueError('Location is required')
            
            service_request.save()
            
            messages.success(request, '✅ Service request has been updated successfully!')
            return redirect('service_requests_web:client_request_detail', pk=service_request.id)
            
        except ValueError:
            # Validation error, re-render form with error message
            pass
        except Exception as e:
            messages.error(request, f'Error updating request: {str(e)}')
    
    context = {
        'service_request': service_request,
        'categories': categories,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/edit_request.html', context)


@login_required
def client_web_complete_request(request, pk):
    """Mark a service request as completed (client marks as finished)"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Check if request can be marked as completed
    if service_request.status != 'in_progress':
        messages.error(request, f'Cannot mark as completed. Request status is: {service_request.get_status_display()}. Only in-progress requests can be marked as finished.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    if request.method == 'POST':
        # Update request status
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()
        
        # Notify worker that client has marked work as finished
        if service_request.assigned_worker:
            try:
                from jobs.notifications import NotificationService
                NotificationService.create_notification(
                    recipient=service_request.assigned_worker.user,
                    title=f"✅ Service Marked as Finished",
                    message=f"Client has marked '{service_request.title}' as finished. Great work!",
                    notification_type='job_completed',
                    related_job_id=service_request.id
                )
            except Exception as e:
                # Don't fail completion if notification fails
                print(f"Failed to send completion notification: {e}")
        
        messages.success(request, '✅ Service request has been marked as finished! You can now rate the worker.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    # If not POST, redirect back to detail page
    return redirect('service_requests_web:client_request_detail', pk=pk)


@login_required
def client_web_upload_screenshot(request, pk):
    """Upload payment screenshot for a service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'payment_screenshot' not in request.FILES:
            messages.error(request, 'Please select a screenshot file to upload.')
            return redirect('service_requests_web:client_request_detail', pk=pk)
        
        # Get the uploaded file
        screenshot = request.FILES['payment_screenshot']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if screenshot.content_type not in allowed_types:
            messages.error(request, 'Invalid file type. Please upload an image file (JPEG, PNG, GIF, or WebP).')
            return redirect('service_requests_web:client_request_detail', pk=pk)
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if screenshot.size > max_size:
            messages.error(request, 'File too large. Maximum size is 5MB.')
            return redirect('service_requests_web:client_request_detail', pk=pk)
        
        # Save the screenshot
        service_request.payment_screenshot = screenshot
        service_request.payment_verified = False  # Reset verification when new screenshot uploaded
        service_request.payment_verified_by = None
        service_request.payment_verified_at = None
        service_request.save()
        
        # Notify admin about new screenshot
        from worker_connect.notification_helpers import notify_system_alert
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            notify_system_alert(
                admin,
                'New Payment Screenshot',
                f'Client {request.user.get_full_name()} uploaded a payment screenshot for request #{service_request.id}'
            )
        
        messages.success(request, '✅ Payment screenshot uploaded successfully! Admin will verify it soon.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    # GET request - show upload form
    context = {
        'service_request': service_request,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/upload_screenshot.html', context)


@login_required
def client_web_history(request):
    """View completed and cancelled service requests history"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    # Get all categories
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    # Base queryset
    requests_list = ServiceRequest.objects.filter(
        client=request.user,
        status__in=['completed', 'cancelled']
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    search_query = request.GET.get('search', '').strip()
    
    # Apply filters
    if status_filter:
        requests_list = requests_list.filter(status=status_filter)
    if category_filter:
        requests_list = requests_list.filter(category_id=category_filter)
    if from_date:
        requests_list = requests_list.filter(created_at__gte=from_date)
    if to_date:
        requests_list = requests_list.filter(created_at__lte=to_date)
    if search_query:
        requests_list = requests_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Calculate stats
    completed_requests = ServiceRequest.objects.filter(client=request.user, status='completed')
    cancelled_requests = ServiceRequest.objects.filter(client=request.user, status='cancelled')
    
    completed_count = completed_requests.count()
    cancelled_count = cancelled_requests.count()
    
    # Total spent (from completed requests with total_price or total_amount)
    total_spent_price = completed_requests.aggregate(total=Sum('total_price'))['total'] or 0
    total_spent_amount = completed_requests.aggregate(total=Sum('total_amount'))['total'] or 0
    total_spent = total_spent_price if total_spent_price > 0 else total_spent_amount
    
    # Total hours
    total_hours = completed_requests.aggregate(total=Sum('total_hours_worked'))['total'] or 0
    
    # Pagination
    paginator = Paginator(requests_list, 15)
    page = request.GET.get('page', 1)
    requests_paginated = paginator.get_page(page)
    
    # Calculate page total
    page_total = sum(
        float(req.total_price or req.total_amount or 0) 
        for req in requests_paginated
    )
    
    context = {
        'requests': requests_paginated,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'from_date': from_date,
        'to_date': to_date,
        'search_query': search_query,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_spent': total_spent,
        'total_hours': total_hours,
        'page_total': page_total,
        'active_menu': 'history'
    }
    
    return render(request, 'service_requests/client/history.html', context)


@login_required
def client_web_rate_worker(request, pk):
    """Rate worker after service completion"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can rate workers.')
        return redirect('home')
    
    service_request = get_object_or_404(
        ServiceRequest,
        pk=pk,
        client=request.user
    )
    
    # Only allow rating for completed services
    if service_request.status != 'completed':
        messages.error(request, 'You can only rate completed services.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    # Check if already rated
    if service_request.client_rating:
        messages.warning(request, 'You have already rated this service.')
        return redirect('service_requests_web:client_request_detail', pk=pk)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review = request.POST.get('review', '').strip()
        
        if not rating or int(rating) < 1 or int(rating) > 5:
            messages.error(request, 'Please provide a valid rating (1-5 stars).')
        else:
            service_request.client_rating = int(rating)
            service_request.client_review = review
            service_request.save()
            
            messages.success(request, 'Thank you for your rating!')
            return redirect('service_requests_web:client_request_detail', pk=pk)
    
    context = {
        'service_request': service_request
    }
    
    return render(request, 'service_requests/client/rate_worker.html', context)


@login_required
def client_web_activity(request, pk):
    """View activity log for a specific service request"""
    if request.user.user_type != 'client':
        messages.error(request, 'Only clients can access this page.')
        return redirect('home')
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Get all activities for this service request
    activity_list = WorkerActivity.objects.filter(
        service_request=service_request
    ).select_related('worker', 'worker__user').order_by('-created_at')
    
    # Filter by activity type if specified
    activity_type = request.GET.get('type')
    if activity_type:
        activity_list = activity_list.filter(activity_type=activity_type)
    
    # Pagination
    paginator = Paginator(activity_list, 20)
    page = request.GET.get('page', 1)
    activities = paginator.get_page(page)
    
    context = {
        'service_request': service_request,
        'activities': activities,
        'activity_type': activity_type,
        'active_menu': 'my_requests'
    }
    
    return render(request, 'service_requests/client/activity.html', context)
