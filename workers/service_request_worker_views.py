"""
Worker API Views for Service Requests
Worker receives assignments, accepts/rejects, tracks time, confirms completion
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
    ServiceRequestSerializer, ServiceRequestListSerializer,
    WorkerResponseSerializer, TimeTrackingSerializer,
    ClockInSerializer, ClockOutSerializer, CompleteServiceSerializer,
    WorkerActivitySerializer, WorkerStatsSerializer,
    ServiceRequestAssignmentSerializer, AssignmentResponseSerializer
)
from workers.models import WorkerProfile
from worker_connect.pagination import paginate_queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_service_request_detail(request, pk):
    """
    Get full detail of a single assigned service request - NEW multi-worker system
    GET /api/v1/worker/service-requests/{pk}/detail/
    Note: pk can be either assignment_id OR service_request_id for backward compatibility
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)

    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)

    # Try to find assignment by assignment ID first (new behavior)
    assignment = ServiceRequestAssignment.objects.filter(
        pk=pk,
        worker=worker_profile
    ).select_related('service_request', 'service_request__client', 'service_request__category').first()
    
    if not assignment:
        # Fallback: try to find by service_request ID (old behavior for backward compatibility)
        service_request = ServiceRequest.objects.filter(pk=pk).first()
        if not service_request:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        assignment = ServiceRequestAssignment.objects.filter(
            service_request=service_request,
            worker=worker_profile
        ).select_related('service_request', 'service_request__client', 'service_request__category').first()
        
        if not assignment:
            return Response(
                {'error': 'This service is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    service_request = assignment.service_request
    serializer = ServiceRequestAssignmentSerializer(assignment)

    # Include time tracking logs for this worker only
    time_logs = service_request.time_logs.filter(worker=worker_profile).order_by('clock_in')
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data

    return Response({
        'assignment': serializer.data,
        'service_request': serializer.data,  # For backward compatibility - now includes flattened fields
        'time_logs': time_logs_data,
        'is_clocked_in': time_logs.filter(clock_out__isnull=True).exists(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_assigned_services(request):
    """
    Get services assigned to this worker - NEW multi-worker system
    Filter: ?status=assigned (assigned, pending, accepted, in_progress, completed)
    LEGACY endpoint updated to use ServiceRequestAssignment
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get assignments - NEW system
    queryset = ServiceRequestAssignment.objects.filter(
        worker=worker_profile
    ).select_related('service_request', 'service_request__client', 'service_request__category').order_by('-assigned_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    return paginate_queryset(request, queryset, ServiceRequestAssignmentSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_pending_assignments(request):
    """Get assignments waiting for worker response - NEW multi-worker system
    LEGACY endpoint updated to use ServiceRequestAssignment"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get pending assignments - NEW system
    queryset = ServiceRequestAssignment.objects.filter(
        worker=worker_profile,
        status='pending'
    ).select_related('service_request', 'service_request__client', 'service_request__category').order_by('-assigned_at')
    
    return paginate_queryset(request, queryset, ServiceRequestAssignmentSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_respond_to_assignment(request, pk):
    """
    Worker accepts or rejects an assignment - NEW multi-worker system
    POST /api/worker/service-requests/{pk}/respond/
    Body: {"accepted": true} or {"accepted": false, "rejection_reason": "Already booked"}
    Note: pk can be assignment_id OR service_request_id for backward compatibility
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Try assignment ID first, fallback to service_request ID
    assignment = ServiceRequestAssignment.objects.filter(
        pk=pk,
        worker=worker_profile
    ).first()
    
    if not assignment:
        # Fallback: find by service_request ID
        service_request = get_object_or_404(ServiceRequest, pk=pk)
        try:
            assignment = ServiceRequestAssignment.objects.get(
                service_request=service_request,
                worker=worker_profile
            )
        except ServiceRequestAssignment.DoesNotExist:
            return Response(
                {'error': 'This service is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    service_request = assignment.service_request
    
    # Check if already responded
    if assignment.worker_accepted is not None:
        return Response(
            {'error': 'You have already responded to this assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = WorkerResponseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accepted = serializer.validated_data['accepted']
    
    if accepted:
        # Accept assignment - NEW system
        assignment.status = 'accepted'
        assignment.worker_accepted = True
        assignment.worker_response_at = timezone.now()
        assignment.save()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='accepted',
            description=f'Accepted assignment: {service_request.title} (Worker {assignment.assignment_number} of {service_request.workers_needed})',
            service_request=service_request,
            location=service_request.location
        )
        
        message = 'Assignment accepted successfully'
    else:
        # Reject assignment - NEW system
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        assignment.status = 'rejected'
        assignment.worker_accepted = False
        assignment.worker_response_at = timezone.now()
        assignment.worker_rejection_reason = rejection_reason
        assignment.save()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='rejected',
            description=f'Rejected assignment: {service_request.title}. Reason: {rejection_reason}',
            service_request=service_request
        )
        
        message = 'Assignment rejected'
    
    response_serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': message,
        'assignment': response_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_clock_in(request, pk):
    """
    Worker clocks in to start work - NEW multi-worker system
    POST /api/worker/service-requests/{pk}/clock-in/
    Body: {"location": "Client address GPS coordinates"} (optional)
    Note: pk can be assignment_id OR service_request_id for backward compatibility
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Try assignment ID first, fallback to service_request ID
    assignment = ServiceRequestAssignment.objects.filter(
        pk=pk,
        worker=worker_profile
    ).select_related('service_request').first()
    
    if not assignment:
        # Fallback: find by service_request ID
        service_request = get_object_or_404(ServiceRequest, pk=pk)
        try:
            assignment = ServiceRequestAssignment.objects.get(
                service_request=service_request,
                worker=worker_profile
            )
        except ServiceRequestAssignment.DoesNotExist:
            return Response(
                {'error': 'This service is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    service_request = assignment.service_request
    
    if assignment.status not in ['accepted', 'in_progress']:
        return Response(
            {'error': 'You must accept the assignment first'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already clocked in (has active time log)
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
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
    
    # Create time log
    time_log = TimeTracking.objects.create(
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
    
    # Update service request status
    if not service_request.work_started_at:
        service_request.work_started_at = timezone.now()
        service_request.status = 'in_progress'
        service_request.save()
        
        # Notify client that work has started
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(
            recipient=service_request.client,
            title="🚀 Work Started on Your Request",
            message=f"{worker_profile.user.get_full_name()} has started working on '{service_request.title}'",
            notification_type='job_assigned',
            content_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'worker': worker_profile.user.get_full_name(),
                'started_at': str(timezone.now())
            }
        )
    
    # Log activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='started',
        description=f'Started work on: {service_request.title} (Worker {assignment.assignment_number})',
        service_request=service_request,
        location=location
    )
    
    time_log_serializer = TimeTrackingSerializer(time_log)
    return Response({
        'message': 'Clocked in successfully',
        'time_log': time_log_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_clock_out(request, pk):
    """
    Worker clocks out to end work - NEW multi-worker system
    POST /api/worker/service-requests/{pk}/clock-out/
    Body: {"location": "GPS coordinates", "notes": "Work completed"} (optional)
    Note: pk can be assignment_id OR service_request_id for backward compatibility
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Try assignment ID first, fallback to service_request ID
    assignment = ServiceRequestAssignment.objects.filter(
        pk=pk,
        worker=worker_profile
    ).select_related('service_request').first()
    
    if not assignment:
        # Fallback: find by service_request ID
        service_request = get_object_or_404(ServiceRequest, pk=pk)
        try:
            assignment = ServiceRequestAssignment.objects.get(
                service_request=service_request,
                worker=worker_profile
            )
        except ServiceRequestAssignment.DoesNotExist:
            return Response(
                {'error': 'This service is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    service_request = assignment.service_request
    
    # Find active time log
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if not active_log:
        return Response(
            {'error': 'No active clock-in found. Please clock in first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ClockOutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    location = serializer.validated_data.get('location', '')
    notes = serializer.validated_data.get('notes', '')
    
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
    
    time_log_serializer = TimeTrackingSerializer(active_log)
    return Response({
        'message': 'Clocked out successfully',
        'time_log': time_log_serializer.data,
        'hours_worked': str(active_log.duration_hours),
        'total_hours_so_far': str(service_request.total_hours_worked)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_complete_service(request, pk):
    """
    Worker confirms service is completed - NEW multi-worker system
    POST /api/worker/service-requests/{pk}/complete/
    Body: {"completion_notes": "All work done, customer satisfied"} (optional)
    Note: pk can be assignment_id OR service_request_id for backward compatibility
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Try assignment ID first, fallback to service_request ID
    assignment = ServiceRequestAssignment.objects.filter(
        pk=pk,
        worker=worker_profile
    ).select_related('service_request').first()
    
    if not assignment:
        # Fallback: find by service_request ID
        service_request = get_object_or_404(ServiceRequest, pk=pk)
        try:
            assignment = ServiceRequestAssignment.objects.get(
                service_request=service_request,
                worker=worker_profile
            )
        except ServiceRequestAssignment.DoesNotExist:
            return Response(
                {'error': 'This service is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    service_request = assignment.service_request
    
    # Check if already completed
    if assignment.status == 'completed':
        return Response(
            {'error': 'Service is already marked as completed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Make sure no active clock-in
    active_log = TimeTracking.objects.filter(
        service_request=service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    if active_log:
        return Response(
            {'error': 'Please clock out before completing the service'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = CompleteServiceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    completion_notes = serializer.validated_data.get('completion_notes', '')
    
    # Mark assignment as completed - NEW system
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
    
    response_serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': 'Service marked as completed',
        'assignment': response_serializer.data,
        'total_hours': str(service_request.total_hours_worked),
        'total_earned': str(assignment.worker_payment)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_activity_history(request):
    """
    Get worker's activity history
    Filter: ?type=completed, ?from_date=2026-01-01, ?to_date=2026-02-01
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    queryset = WorkerActivity.objects.filter(
        worker=worker_profile
    ).select_related('service_request').order_by('-created_at')
    
    # Filter by activity type
    activity_type = request.GET.get('type')
    if activity_type:
        queryset = queryset.filter(activity_type=activity_type)
    
    # Date range filter
    from_date = request.GET.get('from_date')
    if from_date:
        queryset = queryset.filter(created_at__date__gte=from_date)
    
    to_date = request.GET.get('to_date')
    if to_date:
        queryset = queryset.filter(created_at__date__lte=to_date)
    
    return paginate_queryset(request, queryset, WorkerActivitySerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_statistics(request):
    """Get worker's performance statistics"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Total services
    total_services = ServiceRequest.objects.filter(assigned_worker=worker_profile).count()
    completed_services = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='completed'
    ).count()
    in_progress_services = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='in_progress'
    ).count()
    
    # Total hours and earnings
    stats = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='completed'
    ).aggregate(
        total_hours=Sum('total_hours_worked'),
        total_earned=Sum('total_amount')
    )
    
    total_hours_worked = stats['total_hours'] or 0
    total_earned = stats['total_earned'] or 0
    
    # This week stats
    week_start = datetime.now() - timedelta(days=7)
    week_stats = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='completed',
        work_completed_at__gte=week_start
    ).aggregate(
        week_hours=Sum('total_hours_worked'),
        week_earned=Sum('total_amount')
    )
    
    this_week_hours = week_stats['week_hours'] or 0
    this_week_earned = week_stats['week_earned'] or 0
    
    # Average rating from completed service requests
    from django.db.models import Avg
    rating_data = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='completed',
        client_rating__isnull=False
    ).aggregate(avg=Avg('client_rating'))
    average_rating = round(rating_data['avg'], 2) if rating_data['avg'] else None
    
    stats_serializer = WorkerStatsSerializer(data={
        'total_services': total_services,
        'completed_services': completed_services,
        'in_progress_services': in_progress_services,
        'total_hours_worked': total_hours_worked,
        'total_earned': total_earned,
        'average_rating': average_rating,
        'this_week_hours': this_week_hours,
        'this_week_earned': this_week_earned
    })
    
    stats_serializer.is_valid()
    return Response(stats_serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_current_assignment(request):
    """Get worker's current in-progress assignment"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get current assignment
    current = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='in_progress'
    ).select_related('client', 'category').first()
    
    if not current:
        return Response({'message': 'No active assignment'})
    
    # Check if clocked in
    active_clock = TimeTracking.objects.filter(
        service_request=current,
        worker=worker_profile,
        clock_out__isnull=True
    ).first()
    
    serializer = ServiceRequestSerializer(current)
    return Response({
        'service_request': serializer.data,
        'is_clocked_in': active_clock is not None,
        'clock_in_time': active_clock.clock_in if active_clock else None
    })


# ==================== NEW: Multiple Workers Assignment Endpoints ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_my_assignments(request):
    """
    Get all individual assignments for this worker (new multi-worker system)
    GET /api/v1/worker/my-assignments/
    Filter: ?status=pending (pending, accepted, rejected, in_progress, completed)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get assignments for this worker
    queryset = ServiceRequestAssignment.objects.filter(
        worker=worker_profile
    ).select_related(
        'service_request', 
        'service_request__client', 
        'service_request__category',
        'assigned_by'
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    return paginate_queryset(request, queryset, ServiceRequestAssignmentSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_assignment_detail(request, assignment_id):
    """
    Get detail of a specific assignment
    GET /api/v1/worker/my-assignments/{assignment_id}/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    serializer = ServiceRequestAssignmentSerializer(assignment)
    
    # Include time tracking for this worker
    time_logs = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile
    ).order_by('clock_in')
    
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data
    
    return Response({
        'assignment': serializer.data,
        'time_logs': time_logs_data,
        'is_clocked_in': time_logs.filter(clock_out__isnull=True).exists()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_respond_to_assignment_new(request, assignment_id):
    """
    Worker accepts or rejects an individual assignment (new multi-worker system)
    POST /api/v1/worker/my-assignments/{assignment_id}/respond/
    Body: {"accepted": true} or {"accepted": false, "rejection_reason": "Already booked"}
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Check if already responded
    if assignment.status != 'pending':
        return Response(
            {'error': f'Assignment already {assignment.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = AssignmentResponseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accepted = serializer.validated_data['accepted']
    
    if accepted:
        # Accept assignment
        assignment.accept_assignment()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='accepted',
            description=f'Accepted assignment #{assignment.assignment_number}: {assignment.service_request.title}',
            service_request=assignment.service_request,
            location=assignment.service_request.location
        )
        
        message = f'Assignment #{assignment.assignment_number} accepted successfully'
    else:
        # Reject assignment
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        assignment.reject_assignment(rejection_reason)
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='rejected',
            description=f'Rejected assignment #{assignment.assignment_number}: {assignment.service_request.title}. Reason: {rejection_reason}',
            service_request=assignment.service_request
        )
        
        message = f'Assignment #{assignment.assignment_number} rejected'
    
    response_serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': message,
        'assignment': response_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_complete_assignment(request, assignment_id):
    """
    Worker marks their individual assignment as completed
    POST /api/v1/worker/my-assignments/{assignment_id}/complete/
    Body: {"notes": "Job completed successfully"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    assignment = get_object_or_404(
        ServiceRequestAssignment,
        id=assignment_id,
        worker=worker_profile
    )
    
    # Verify assignment is in progress
    if assignment.status not in ['accepted', 'in_progress']:
        return Response(
            {'error': f'Cannot complete assignment with status: {assignment.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if clocked in
    active_clock = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker_profile,
        clock_out__isnull=True
    ).exists()
    
    if active_clock:
        return Response(
            {'error': 'Please clock out before completing the assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    completion_notes = request.data.get('notes', '')
    assignment.mark_completed(completion_notes)
    
    # Log activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='completed',
        description=f'Completed assignment #{assignment.assignment_number}: {assignment.service_request.title}',
        service_request=assignment.service_request
    )
    
    # Update worker profile stats
    worker_profile.completed_jobs = (worker_profile.completed_jobs or 0) + 1
    worker_profile.save()
    
    serializer = ServiceRequestAssignmentSerializer(assignment)
    return Response({
        'message': 'Assignment completed successfully',
        'assignment': serializer.data
    })
