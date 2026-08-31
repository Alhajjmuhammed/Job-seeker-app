from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from workers.models import WorkerProfile, Category
from .models import ClientProfile
from .forms import ClientProfileForm
import logging
from decimal import Decimal

from jobs.service_request_models import ServiceRequest
from .booking_validation import (
    clean_workers_needed, check_text_lengths, check_dates)

logger = logging.getLogger(__name__)


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
        ).exclude(
            service_assignments__status__in=['pending', 'accepted', 'in_progress']
        ).distinct().count()
        
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
        ).exclude(
            service_assignments__status__in=['pending', 'accepted', 'in_progress']
        ).distinct().count()
        
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
            # Same rules the other two booking paths apply, from one shared
            # validator. Nonsense counts used to be clamped silently: 0 and -5
            # became 1, and 100000 became a crew of a hundred.
            workers_needed, workers_error = clean_workers_needed(
                request.POST.get('workers_needed', '1'))
            if workers_error:
                messages.error(request, workers_error)
                return redirect('clients:request_service', category_id=category.id)

            text_error = check_text_lengths(request.POST)
            if text_error:
                messages.error(request, text_error)
                return redirect('clients:request_service', category_id=category.id)
            
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
            
            # Calculate duration and pricing. Keep this a Decimal - mixing
            # float and Decimal raises TypeError once the fee is added in.
            daily_rate = category.daily_rate or Decimal('0.00')
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

            date_error = check_dates(service_start_date, service_end_date, preferred_date)
            if date_error:
                messages.error(request, date_error)
                return redirect('clients:request_service', category_id=category.id)

            # Price per request: (category amount x workers) + one service
            # fee. duration_days above is scheduling information only. This is
            # the third booking entry point in the codebase - all three now
            # price through the same model method so they cannot disagree.
            quote = ServiceRequest.quote(category, workers_needed)
            service_fee = quote['service_fee']
            total_price = quote['total_price']
            
            # Get payment data
            payment_method = request.POST.get('payment_method', 'pending')
            payment_transaction_id = request.POST.get('payment_transaction_id', '')
            payment_screenshot = request.FILES.get('payment_screenshot')
            
            # Check worker availability before creating request
            available_workers = WorkerProfile.objects.filter(
                categories=category,
                availability='available',
                verification_status='verified'
            ).exclude(
                service_assignments__status__in=['pending', 'accepted', 'in_progress']
            ).distinct().count()
            
            # Inform client about availability
            if workers_needed > available_workers:
                if available_workers == 0:
                    messages.warning(request, 
                        f'⚠️ Currently no available workers for {category.name}. '
                        'Your request will be queued and processed when workers become available.'
                    )
                else:
                    messages.info(request, 
                        f'ℹ️ You requested {workers_needed} worker(s), but only {available_workers} '
                        f'available. Your request is accepted and will be prioritized.'
                    )
            else:
                messages.success(request, 
                    f'✅ {available_workers} worker(s) available for your request.'
                )
            
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
                # snapshot the fee so a later category change cannot rewrite history
                service_fee=service_fee,
                total_price=total_price,
                preferred_date=preferred_date if preferred_date else None,
                preferred_time=preferred_time if preferred_time else None,
                service_start_date=service_start_date if service_start_date else None,
                service_end_date=service_end_date if service_end_date else None,
                # client_notes is NOT NULL - passing None when the client left
                # the box empty raised a constraint error and failed the whole
                # booking, which is the common case.
                client_notes=client_notes or '',
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
            
            messages.success(request, 
                f'Your {category.name} service request has been submitted! '
                f'Total price: TSH {total_price:.2f}. '
                'Our team will assign a qualified worker and notify you within 2-4 hours.'
            )
            return redirect('service_requests_web:client_request_detail', pk=service_request.id)
            
        except Exception as e:
            logger.exception('Service request creation failed')
            messages.error(request, 'Could not create the service request. Please check the details and try again.')
    
    # Get service statistics
    available_workers = WorkerProfile.objects.filter(
        categories=category,
        verification_status='verified',
        availability='available'
    ).exclude(
        service_assignments__status__in=['pending', 'accepted', 'in_progress']
    ).distinct().count()
    
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
    
    # Fetch worker assignments - only show accepted/in_progress/completed (not pending or rejected)
    # Clients should only see workers who have accepted their request
    assignments = service_request.assignments.filter(
        status__in=['accepted', 'in_progress', 'completed']
    ).select_related('worker__user').order_by('id')
    assignments_count = assignments.count()
    
    context = {
        'request': service_request,
        'assignments': assignments,
        'assignments_count': assignments_count,
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
