"""
Worker Views for Individual ServiceRequestAssignments
Each worker sees ONLY their own individual assignment (not shared with other workers)
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking, WorkerActivity
from jobs.service_request_serializers import (
    ServiceRequestSerializer,
    ServiceRequestAssignmentSerializer, 
    AssignmentResponseSerializer,
    TimeTrackingSerializer, 
    ClockInSerializer, 
    ClockOutSerializer
)
from workers.models import WorkerProfile
from worker_connect.pagination import paginate_queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_my_assignments(request):
    """
    Get MY individual assignments (ServiceRequestAssignment records)
    Each worker sees ONLY their own assignment, not other workers' assignments
    
    Filter: ?status=pending (pending, accepted, rejected, in_progress, completed, cancelled)
    GET /api/v1/worker/my-assignments/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignments (isolated view for this worker only)
    queryset = ServiceRequestAssignment.objects.filter(
        worker=worker_profile
    ).select_related(
        'service_request', 
        'service_request__client', 
        'service_request__category',
        'assigned_by'
    ).order_by('-assigned_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    if date_from:
        queryset = queryset.filter(assigned_at__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        queryset = queryset.filter(assigned_at__lte=date_to)
    
    return paginate_queryset(request, queryset, ServiceRequestAssignmentSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_pending_assignments(request):
    """
    Get MY assignments waiting for my response (newly assigned to me)
    GET /api/v1/worker/my-assignments/pending/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get assignments assigned to ME but not yet responded
    queryset = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='pending',
        worker_accepted__isnull=True
    ).select_related(
        'service_request', 
        'service_request__client', 
        'service_request__category'
    ).order_by('-assigned_at')
    
    return paginate_queryset(request, queryset, ServiceRequestAssignmentSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_assignment_detail(request, assignment_id):
    """
    Get full detail of MY specific assignment
    GET /api/v1/worker/my-assignments/{assignment_id}/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignment (not someone else's)
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    serializer = ServiceRequestAssignmentSerializer(assignment)
    
    # Include time tracking logs for MY work on this assignment
    time_logs = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile
    ).order_by('clock_in')
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data
    
    # Check if I'm currently clocked in
    is_clocked_in = time_logs.filter(clock_out__isnull=True).exists()
    
    return Response({
        'assignment': serializer.data,
        'time_logs': time_logs_data,
        'is_clocked_in': is_clocked_in,
        'total_hours_worked': assignment.total_hours_worked or 0,
        'my_payment': str(assignment.worker_payment) if assignment.worker_payment else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_respond_to_assignment(request, assignment_id):
    """
    I accept or reject MY individual assignment
    Other workers' responses do NOT affect my assignment
    
    POST /api/v1/worker/my-assignments/{assignment_id}/respond/
    Body: {"accepted": true} or {"accepted": false, "rejection_reason": "Already booked"}
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignment
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Check if I already responded
    if assignment.worker_accepted is not None:
        return Response(
            {'error': 'You have already responded to this assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = AssignmentResponseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accepted = serializer.validated_data['accepted']
    
    if accepted:
        # I accept MY assignment
        rejection_reason = None
        assignment.accept_assignment()
        
        # Log MY activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='accepted',
            description=f'Accepted assignment: {assignment.service_request.title} (Assignment #{assignment.assignment_number})',
            service_request=assignment.service_request,
            location=assignment.service_request.location
        )
        
        # Notify client that I accepted
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(
            recipient=assignment.service_request.client,
            title="✅ Worker Accepted Your Request",
            message=f"{worker_profile.user.get_full_name()} accepted your service request: '{assignment.service_request.title}'",
            notification_type='job_accepted',
            content_object=assignment.service_request,
            extra_data={
                'service_request_id': assignment.service_request.id,
                'assignment_id': assignment.id,
                'worker': worker_profile.user.get_full_name(),
                'assignment_number': assignment.assignment_number
            }
        )
        
        message = 'Assignment accepted successfully'
    else:
        # I reject MY assignment
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        assignment.reject_assignment(rejection_reason)
        
        # Log MY activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='rejected',
            description=f'Rejected assignment: {assignment.service_request.title}. Reason: {rejection_reason}',
            service_request=assignment.service_request
        )
        
        # Notify admin that I rejected (admin may need to find replacement)
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(
            recipient=assignment.assigned_by,
            title="❌ Worker Rejected Assignment",
            message=f"{worker_profile.user.get_full_name()} rejected: '{assignment.service_request.title}'. Reason: {rejection_reason}",
            notification_type='job_rejected',
            content_object=assignment.service_request,
            extra_data={
                'service_request_id': assignment.service_request.id,
                'assignment_id': assignment.id,
                'worker': worker_profile.user.get_full_name(),
                'rejection_reason': rejection_reason
            }
        )
        
        message = 'Assignment rejected'
    
    response_serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': message,
        'assignment': response_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_clock_in_assignment(request, assignment_id):
    """
    I clock in to start work on MY assignment
    POST /api/v1/worker/my-assignments/{assignment_id}/clock-in/
    Body: {"location": "GPS coordinates"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignment
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Check if I accepted it
    if assignment.worker_accepted != True:
        return Response(
            {'error': 'You must accept the assignment first'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if I'm already clocked in for this assignment
    active_log = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if active_log:
        return Response(
            {'error': 'You are already clocked in. Please clock out first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ClockInSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    location = serializer.validated_data.get('location', '')
    
    # Create time log for MY work
    time_log = TimeTracking.objects.create(
        service_request=assignment.service_request,
        worker=worker_profile,
        clock_in=timezone.now(),
        clock_in_location=location
    )
    
    # Update MY assignment status to in_progress
    if assignment.status == 'accepted':
        assignment.status = 'in_progress'
        assignment.work_started_at = timezone.now()
        assignment.save()
    
    # Log MY activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='started',
        description=f'Started work on: {assignment.service_request.title} (Assignment #{assignment.assignment_number})',
        service_request=assignment.service_request,
        location=location
    )
    
    time_log_serializer = TimeTrackingSerializer(time_log)
    return Response({
        'message': 'Clocked in successfully',
        'time_log': time_log_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_clock_out_assignment(request, assignment_id):
    """
    I clock out to end work session on MY assignment
    POST /api/v1/worker/my-assignments/{assignment_id}/clock-out/
    Body: {"location": "GPS coordinates", "notes": "Work notes"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignment
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Find MY active time log
    active_log = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if not active_log:
        return Response(
            {'error': 'You are not clocked in. Please clock in first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ClockOutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    location = serializer.validated_data.get('location', '')
    notes = serializer.validated_data.get('notes', '')
    
    # Clock out
    active_log.clock_out = timezone.now()
    active_log.clock_out_location = location
    active_log.notes = notes
    active_log.save()
    
    # Calculate hours worked
    hours_worked = active_log.hours_worked
    
    # Update total hours on MY assignment
    if assignment.total_hours_worked:
        assignment.total_hours_worked += hours_worked
    else:
        assignment.total_hours_worked = hours_worked
    assignment.save()
    
    # Log MY activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='clocked_out',
        description=f'Clocked out from: {assignment.service_request.title} ({hours_worked:.2f} hours)',
        service_request=assignment.service_request,
        location=location
    )
    
    time_log_serializer = TimeTrackingSerializer(active_log)
    return Response({
        'message': 'Clocked out successfully',
        'time_log': time_log_serializer.data,
        'hours_worked': hours_worked,
        'total_hours': assignment.total_hours_worked
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_complete_assignment(request, assignment_id):
    """
    I mark MY assignment as completed
    Each worker completes their assignment independently
    
    POST /api/v1/worker/my-assignments/{assignment_id}/complete/
    Body: {"completion_notes": "Finished all tasks"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get MY assignment
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Check if I accepted it
    if assignment.worker_accepted != True:
        return Response(
            {'error': 'Cannot complete unaccepted assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already completed
    if assignment.status == 'completed':
        return Response(
            {'error': 'Assignment already completed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Make sure I'm not clocked in
    active_log = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).exists()
    
    if active_log:
        return Response(
            {'error': 'Please clock out before completing the assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    completion_notes = request.data.get('completion_notes', '')
    
    # Mark MY assignment as completed
    assignment.mark_completed(completion_notes)
    
    # Calculate MY payment
    assignment.calculate_payment()
    
    # Log MY activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='completed',
        description=f'Completed assignment: {assignment.service_request.title} (Assignment #{assignment.assignment_number})',
        service_request=assignment.service_request,
        location=assignment.service_request.location
    )
    
    # Notify client that I completed MY part
    from worker_connect.notification_service import NotificationService
    NotificationService.create_notification(
        recipient=assignment.service_request.client,
        title="✅ Worker Completed Their Assignment",
        message=f"{worker_profile.user.get_full_name()} completed their work on: '{assignment.service_request.title}'",
        notification_type='job_completed',
        content_object=assignment.service_request,
        extra_data={
            'service_request_id': assignment.service_request.id,
            'assignment_id': assignment.id,
            'worker': worker_profile.user.get_full_name(),
            'assignment_number': assignment.assignment_number,
            'total_hours': assignment.total_hours_worked,
            'payment': str(assignment.worker_payment)
        }
    )
    
    response_serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': 'Assignment completed successfully',
        'assignment': response_serializer.data,
        'payment': str(assignment.worker_payment),
        'total_hours_worked': assignment.total_hours_worked
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_assignment_stats(request):
    """
    Get MY statistics (from MY assignments only)
    GET /api/v1/worker/my-assignments/stats/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # My assignments
    my_assignments = ServiceRequestAssignment.objects.filter(worker=worker_profile)
    
    total_assignments = my_assignments.count()
    pending = my_assignments.filter(status='pending').count()
    accepted = my_assignments.filter(status='accepted').count()
    in_progress = my_assignments.filter(status='in_progress').count()
    completed = my_assignments.filter(status='completed').count()
    rejected = my_assignments.filter(status='rejected').count()
    
    # Total earnings from completed assignments
    total_earnings = my_assignments.filter(
        status='completed'
    ).aggregate(total=Sum('worker_payment'))['total'] or 0
    
    # Total hours worked
    total_hours = my_assignments.filter(
        status='completed'
    ).aggregate(total=Sum('total_hours_worked'))['total'] or 0
    
    # This week's stats
    week_ago = timezone.now() - timedelta(days=7)
    week_completed = my_assignments.filter(
        status='completed',
        work_completed_at__gte=week_ago
    ).count()
    
    week_earnings = my_assignments.filter(
        status='completed',
        work_completed_at__gte=week_ago
    ).aggregate(total=Sum('worker_payment'))['total'] or 0
    
    return Response({
        'total_assignments': total_assignments,
        'pending': pending,
        'accepted': accepted,
        'in_progress': in_progress,
        'completed': completed,
        'rejected': rejected,
        'total_earnings': str(total_earnings),
        'total_hours_worked': float(total_hours) if total_hours else 0,
        'this_week_completed': week_completed,
        'this_week_earnings': str(week_earnings)
    })
