"""
Web Views for Workers - Service Request System
Workers can use web browser to accept jobs, clock in/out, and view activity
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking, WorkerActivity
from workers.models import WorkerProfile


@login_required
def worker_web_dashboard(request):
    """Worker web dashboard - overview of assignments and stats"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get statistics - NEW multi-worker system
    total_services = ServiceRequestAssignment.objects.filter(worker=worker_profile).count()
    completed = ServiceRequestAssignment.objects.filter(worker=worker_profile, status='completed').count()
    in_progress = ServiceRequestAssignment.objects.filter(worker=worker_profile, status='in_progress').count()
    
    # Earnings - NEW multi-worker system
    earnings_data = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='completed'
    ).aggregate(
        total_hours=Sum('total_hours_worked'),
        total_earned=Sum('worker_payment')
    )
    
    total_hours = earnings_data['total_hours'] or 0
    total_earned = earnings_data['total_earned'] or 0
    
    # This week - NEW multi-worker system
    week_start = datetime.now() - timedelta(days=7)
    week_data = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='completed',
        work_completed_at__gte=week_start
    ).aggregate(
        week_hours=Sum('total_hours_worked'),
        week_earned=Sum('worker_payment')
    )
    
    week_hours = week_data['week_hours'] or 0
    week_earned = week_data['week_earned'] or 0
    
    # Pending assignments - NEW multi-worker system
    pending = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='pending'
    ).count()
    
    # Current assignment - NEW multi-worker system
    current_assignment_obj = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='in_progress'
    ).select_related('service_request', 'service_request__client', 'service_request__category').first()
    
    current_assignment = current_assignment_obj.service_request if current_assignment_obj else None
    
    # Check if clocked in
    is_clocked_in = False
    if current_assignment:
        is_clocked_in = TimeTracking.objects.filter(
            service_request=current_assignment,
            worker=worker_profile,
            clock_out__isnull=True
        ).exists()
    
    # Recent activity
    recent_activity = WorkerActivity.objects.filter(
        worker=worker_profile
    ).select_related('service_request').order_by('-created_at')[:5]
    
    context = {
        'total_services': total_services,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'total_hours': total_hours,
        'total_earned': total_earned,
        'week_hours': week_hours,
        'week_earned': week_earned,
        'current_assignment': current_assignment,
        'current_assignment_obj': current_assignment_obj,  # Assignment object with correct ID
        'is_clocked_in': is_clocked_in,
        'recent_activity': recent_activity,
        'active_menu': 'dashboard'
    }
    
    return render(request, 'service_requests/worker/dashboard.html', context)


@login_required
def worker_web_assignments(request):
    """List all worker assignments"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignments - NEW multi-worker system
    assignments_list = ServiceRequestAssignment.objects.filter(
        worker=worker_profile
    ).select_related('service_request', 'service_request__client', 'service_request__category').order_by('-assigned_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        assignments_list = assignments_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(assignments_list, 10)
    page = request.GET.get('page', 1)
    assignments = paginator.get_page(page)
    
    context = {
        'assignments': assignments,
        'status_filter': status_filter,
        'active_menu': 'assignments'
    }
    
    return render(request, 'service_requests/worker/assignments.html', context)


@login_required
def worker_web_pending_assignments(request):
    """View assignments waiting for response"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get pending assignments - NEW multi-worker system
    pending = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='pending'
    ).select_related('service_request', 'service_request__client', 'service_request__category').order_by('-assigned_at')
    
    context = {
        'pending_assignments': pending,
        'active_menu': 'pending'
    }
    
    return render(request, 'service_requests/worker/pending.html', context)


@login_required
def worker_web_respond_assignment(request, pk):
    """Accept or reject assignment - NEW multi-worker system"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignment record (not service request) - NEW system
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        pk=pk,
        worker=worker_profile
    )
    
    if assignment.worker_accepted is not None:
        messages.warning(request, 'You have already responded to this assignment.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            # Accept assignment
            assignment.status = 'accepted'
            assignment.worker_accepted = True
            assignment.worker_response_at = timezone.now()
            assignment.save()
            
            # Log activity
            WorkerActivity.log_activity(
                worker=worker_profile,
                activity_type='accepted',
                description=f'Accepted assignment: {assignment.service_request.title} (Worker {assignment.assignment_number} of {assignment.service_request.workers_needed})',
                service_request=assignment.service_request,
                location=assignment.service_request.location
            )
            
            messages.success(request, '✅ Assignment accepted! You can now start work.')
            return redirect('service_requests_web:worker_assignment_detail', pk=pk)
            
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            
            # Reject assignment
            assignment.status = 'rejected'
            assignment.worker_accepted = False
            assignment.worker_response_at = timezone.now()
            assignment.worker_rejection_reason = reason
            assignment.save()
            
            # Log activity
            WorkerActivity.log_activity(
                worker=worker_profile,
                activity_type='rejected',
                description=f'Rejected assignment: {assignment.service_request.title}. Reason: {reason}',
                service_request=assignment.service_request
            )
            
            messages.info(request, 'Assignment rejected.')
            return redirect('service_requests_web:worker_assignments')
    
    context = {
        'assignment': assignment,
        'service_request': assignment.service_request  # For template compatibility
    }
    
    return render(request, 'service_requests/worker/respond.html', context)


@login_required
def worker_web_assignment_detail(request, pk):
    """View assignment details - NEW multi-worker system"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignment record (not service request) - NEW system
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        pk=pk,
        worker=worker_profile
    )
    
    service_request = assignment.service_request
    
    # Get time logs for this worker only
    time_logs = service_request.time_logs.filter(worker=worker_profile).order_by('-clock_in')
    
    # Check if currently clocked in
    active_clock = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    context = {
        'assignment': assignment,
        'service_request': service_request,  # For template compatibility
        'time_logs': time_logs,
        'active_clock': active_clock,
        'is_clocked_in': active_clock is not None
    }
    
    return render(request, 'service_requests/worker/assignment_detail.html', context)


@login_required
def worker_web_clock_in(request, pk):
    """Clock in to start work - NEW multi-worker system"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignment - NEW system
    assignment = get_object_or_404(ServiceRequestAssignment, pk=pk, worker=worker_profile)
    service_request = assignment.service_request
    
    if assignment.status not in ['accepted', 'in_progress']:
        messages.error(request, 'You must accept the assignment first.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    # Check if already clocked in
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if active_log:
        messages.warning(request, 'You are already clocked in.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    if request.method == 'POST':
        location = request.POST.get('location', '')
        
        # Create time log
        TimeTracking.objects.create(
            service_request=service_request,
            worker=worker_profile,
            clock_in=timezone.now(),
            clock_in_location=location
        )
        
        # Update assignment status to in_progress
        if assignment.status == 'accepted':
            assignment.status = 'in_progress'
            assignment.work_started_at = timezone.now()
            assignment.save()
        
        # Update service request
        if not service_request.work_started_at:
            service_request.work_started_at = timezone.now()
            service_request.status = 'in_progress'
            service_request.save()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='started',
            description=f'Started work on: {service_request.title} (Worker {assignment.assignment_number})',
            service_request=service_request,
            location=location
        )
        
        messages.success(request, '⏰ Clocked in! Timer started.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    context = {
        'assignment': assignment,
        'service_request': service_request
    }
    
    return render(request, 'service_requests/worker/clock_in.html', context)


@login_required
def worker_web_clock_out(request, pk):
    """Clock out to end work - NEW multi-worker system"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignment - NEW system
    assignment = get_object_or_404(ServiceRequestAssignment, pk=pk, worker=worker_profile)
    service_request = assignment.service_request
    
    # Find active time log
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if not active_log:
        messages.error(request, 'No active clock-in found.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    if request.method == 'POST':
        location = request.POST.get('location', '')
        notes = request.POST.get('notes', '')
        
        # Clock out
        active_log.clock_out_now(notes=notes, location=location)
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='paused',
            description=f'Clocked out from: {service_request.title}',
            service_request=service_request,
            location=location,
            duration=timedelta(hours=float(active_log.duration_hours))
        )
        
        messages.success(request, f'⏰ Clocked out! Worked {active_log.duration_hours} hours.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    context = {
        'assignment': assignment,
        'service_request': service_request,
        'active_log': active_log
    }
    
    return render(request, 'service_requests/worker/clock_out.html', context)


@login_required
def worker_web_complete_service(request, pk):
    """Mark service as completed - NEW multi-worker system"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get assignment - NEW system
    assignment = get_object_or_404(ServiceRequestAssignment, pk=pk, worker=worker_profile)
    service_request = assignment.service_request
    
    if assignment.status == 'completed':
        messages.warning(request, 'Service is already completed.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    # Check no active clock
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if active_log:
        messages.error(request, 'Please clock out before completing the service.')
        return redirect('service_requests_web:worker_assignment_detail', pk=pk)
    
    if request.method == 'POST':
        completion_notes = request.POST.get('completion_notes', '')
        
        # Mark assignment as completed
        assignment.status = 'completed'
        assignment.work_completed_at = timezone.now()
        assignment.completion_notes = completion_notes
        assignment.save()
        
        # Check if all assignments are completed
        all_completed = not service_request.assignments.exclude(
            status='completed'
        ).filter(
            status__in=['accepted', 'in_progress']
        ).exists()
        
        if all_completed:
            service_request.status = 'completed'
            service_request.work_completed_at = timezone.now()
            service_request.save()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='completed',
            description=f'Completed service: {service_request.title} (Worker {assignment.assignment_number})',
            service_request=service_request,
            location=service_request.location,
            amount_earned=assignment.worker_payment
        )
        
        messages.success(request, f'✅ Service completed! Earned: TSH {assignment.worker_payment}')
        return redirect('service_requests_web:worker_activity')
    
    context = {
        'assignment': assignment,
        'service_request': service_request
    }
    
    return render(request, 'service_requests/worker/complete.html', context)


@login_required
def worker_web_activity(request):
    """View worker activity history"""
    if request.user.user_type != 'worker':
        messages.error(request, 'Only workers can access this page.')
        return redirect('home')
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        messages.error(request, 'Worker profile not found.')
        return redirect('home')
    
    # Get activity
    activity_list = WorkerActivity.objects.filter(
        worker=worker_profile
    ).select_related('service_request').order_by('-created_at')
    
    # Filter
    activity_type = request.GET.get('type')
    if activity_type:
        activity_list = activity_list.filter(activity_type=activity_type)
    
    # Pagination
    paginator = Paginator(activity_list, 20)
    page = request.GET.get('page', 1)
    activities = paginator.get_page(page)
    
    context = {
        'activities': activities,
        'activity_type': activity_type,
        'active_menu': 'activity'
    }
    
    return render(request, 'service_requests/worker/activity.html', context)
