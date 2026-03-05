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

from jobs.service_request_models import ServiceRequest, TimeTracking, WorkerActivity
from jobs.service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    WorkerResponseSerializer, TimeTrackingSerializer,
    ClockInSerializer, ClockOutSerializer, CompleteServiceSerializer,
    WorkerActivitySerializer, WorkerStatsSerializer
)
from workers.models import WorkerProfile
from worker_connect.pagination import paginate_queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_service_request_detail(request, pk):
    """
    Get full detail of a single assigned service request
    GET /api/v1/worker/service-requests/{pk}/detail/
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)

    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)

    service_request = get_object_or_404(
        ServiceRequest, pk=pk, assigned_worker=worker_profile
    )

    serializer = ServiceRequestSerializer(service_request)

    # Include time tracking logs
    time_logs = service_request.time_logs.all().order_by('clock_in')
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data

    return Response({
        'service_request': serializer.data,
        'time_logs': time_logs_data,
        'is_clocked_in': service_request.time_logs.filter(clock_out__isnull=True).exists(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_assigned_services(request):
    """
    Get services assigned to this worker
    Filter: ?status=assigned (assigned, in_progress, completed)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    queryset = ServiceRequest.objects.filter(
        assigned_worker=worker_profile
    ).select_related('client', 'category').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    return paginate_queryset(request, queryset, ServiceRequestListSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_pending_assignments(request):
    """Get assignments waiting for worker response (newly assigned)"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get services assigned but not yet responded to
    queryset = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='assigned',
        worker_accepted__isnull=True
    ).select_related('client', 'category').order_by('-assigned_at')
    
    return paginate_queryset(request, queryset, ServiceRequestSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_respond_to_assignment(request, pk):
    """
    Worker accepts or rejects an assignment
    POST /api/worker/service-requests/{pk}/respond/
    Body: {"accepted": true} or {"accepted": false, "rejection_reason": "Already booked"}
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Verify this worker is assigned
    if service_request.assigned_worker != worker_profile:
        return Response(
            {'error': 'This service is not assigned to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already responded
    if service_request.worker_accepted is not None:
        return Response(
            {'error': 'You have already responded to this assignment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = WorkerResponseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    accepted = serializer.validated_data['accepted']
    
    if accepted:
        # Accept assignment
        service_request.worker_accept()
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='accepted',
            description=f'Accepted assignment: {service_request.title}',
            service_request=service_request,
            location=service_request.location
        )
        
        message = 'Assignment accepted successfully'
    else:
        # Reject assignment
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        service_request.worker_reject(rejection_reason)
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker_profile,
            activity_type='rejected',
            description=f'Rejected assignment: {service_request.title}. Reason: {rejection_reason}',
            service_request=service_request
        )
        
        message = 'Assignment rejected'
    
    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': message,
        'service_request': response_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def worker_clock_in(request, pk):
    """
    Worker clocks in to start work
    POST /api/worker/service-requests/{pk}/clock-in/
    Body: {"location": "Client address GPS coordinates"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Verify worker is assigned and accepted
    if service_request.assigned_worker != worker_profile:
        return Response(
            {'error': 'This service is not assigned to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if service_request.worker_accepted != True:
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
    
    # Update service request status
    if not service_request.work_started_at:
        service_request.work_started_at = timezone.now()
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
        description=f'Started work on: {service_request.title}',
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
    Worker clocks out to end work
    POST /api/worker/service-requests/{pk}/clock-out/
    Body: {"location": "GPS coordinates", "notes": "Work completed"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Verify worker is assigned
    if service_request.assigned_worker != worker_profile:
        return Response(
            {'error': 'This service is not assigned to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
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
    Worker confirms service is completed
    POST /api/worker/service-requests/{pk}/complete/
    Body: {"completion_notes": "All work done, customer satisfied"} (optional)
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Verify worker is assigned
    if service_request.assigned_worker != worker_profile:
        return Response(
            {'error': 'This service is not assigned to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already completed
    if service_request.status == 'completed':
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
    
    # Mark as completed
    service_request.mark_completed_by_worker(completion_notes)
    
    # Log activity
    WorkerActivity.log_activity(
        worker=worker_profile,
        activity_type='completed',
        description=f'Completed service: {service_request.title}',
        service_request=service_request,
        location=service_request.location,
        amount_earned=service_request.total_amount
    )
    
    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Service marked as completed',
        'service_request': response_serializer.data,
        'total_hours': str(service_request.total_hours_worked),
        'total_earned': str(service_request.total_amount)
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
