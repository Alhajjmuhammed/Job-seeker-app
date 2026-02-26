"""
Admin Views for Service Request Management
Admin assigns workers to service requests
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta

from jobs.service_request_models import ServiceRequest, TimeTracking, WorkerActivity
from jobs.service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    AdminAssignWorkerSerializer, TimeTrackingSerializer
)
from workers.models import WorkerProfile, Category
from worker_connect.pagination import paginate_queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_service_requests(request):
    """
    Get all service requests for admin dashboard
    Filter by status: ?status=pending
    Filter by urgency: ?urgency=urgent
    Search: ?search=plumbing
    """
    queryset = ServiceRequest.objects.all().select_related(
        'client', 'category', 'assigned_worker', 'assigned_worker__user'
    ).order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    urgency_filter = request.GET.get('urgency')
    if urgency_filter:
        queryset = queryset.filter(urgency=urgency_filter)
    
    category_filter = request.GET.get('category')
    if category_filter:
        queryset = queryset.filter(category_id=category_filter)
    
    city_filter = request.GET.get('city')
    if city_filter:
        queryset = queryset.filter(city__icontains=city_filter)
    
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    return paginate_queryset(request, queryset, ServiceRequestListSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_service_request_detail(request, pk):
    """Get detailed service request for admin"""
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    serializer = ServiceRequestSerializer(service_request)
    
    # Get time logs
    time_logs = service_request.time_logs.all()
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data
    
    # Get available workers for this category
    if service_request.category:
        available_workers = WorkerProfile.objects.filter(
            categories=service_request.category,
            verification_status='verified'
        ).exclude(
            availability='offline'
        ).select_related('user')[:10]
        
        workers_data = [{
            'id': w.id,
            'name': w.user.get_full_name(),
            'availability': w.availability,
            'hourly_rate': str(w.hourly_rate) if w.hourly_rate else None,
            'completed_jobs': w.completed_jobs,
            'city': w.city
        } for w in available_workers]
    else:
        workers_data = []
    
    return Response({
        'service_request': serializer.data,
        'time_logs': time_logs_data,
        'available_workers': workers_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_assign_worker(request, pk):
    """
    Admin assigns a worker to a service request
    POST /api/admin/service-requests/{pk}/assign/
    Body: {"worker_id": 123, "admin_notes": "Best available plumber"}
    """
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Validate request is not already completed or cancelled
    if service_request.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'Cannot assign worker to {service_request.status} request'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = AdminAssignWorkerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    worker_id = serializer.validated_data['worker_id']
    admin_notes = serializer.validated_data.get('admin_notes', '')
    
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        
        # Check if worker has this category
        if service_request.category and not worker.categories.filter(id=service_request.category.id).exists():
            return Response(
                {'error': 'Worker does not have the required category'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Assign worker
        service_request.assign_worker(worker, request.user, admin_notes)
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker,
            activity_type='assigned',
            description=f'Assigned to: {service_request.title}',
            service_request=service_request,
            location=service_request.location
        )
        
        serializer = ServiceRequestSerializer(service_request)
        return Response({
            'message': 'Worker assigned successfully',
            'service_request': serializer.data
        })
        
    except WorkerProfile.DoesNotExist:
        return Response(
            {'error': 'Worker not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_reassign_worker(request, pk):
    """
    Admin reassigns a different worker (if first one rejected or unavailable)
    """
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    if service_request.status == 'completed':
        return Response(
            {'error': 'Cannot reassign completed service'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # If there was a previous worker, log the change
    previous_worker = service_request.assigned_worker
    
    serializer = AdminAssignWorkerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    worker_id = serializer.validated_data['worker_id']
    admin_notes = serializer.validated_data.get('admin_notes', '')
    
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        
        # Reset worker response fields
        service_request.worker_accepted = None
        service_request.worker_response_at = None
        service_request.worker_rejection_reason = ''
        
        # Assign new worker
        service_request.assign_worker(worker, request.user, admin_notes)
        
        # Log activity
        WorkerActivity.log_activity(
            worker=worker,
            activity_type='assigned',
            description=f'Reassigned to: {service_request.title}',
            service_request=service_request,
            location=service_request.location
        )
        
        serializer = ServiceRequestSerializer(service_request)
        return Response({
            'message': 'Worker reassigned successfully',
            'service_request': serializer.data
        })
        
    except WorkerProfile.DoesNotExist:
        return Response(
            {'error': 'Worker not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_dashboard_stats(request):
    """Get statistics for admin dashboard"""
    
    # Service request stats
    total_requests = ServiceRequest.objects.count()
    pending_requests = ServiceRequest.objects.filter(status='pending').count()
    assigned_requests = ServiceRequest.objects.filter(status='assigned').count()
    in_progress_requests = ServiceRequest.objects.filter(status='in_progress').count()
    completed_requests = ServiceRequest.objects.filter(status='completed').count()
    
    # Urgent requests needing attention
    urgent_pending = ServiceRequest.objects.filter(
        status='pending',
        urgency__in=['urgent', 'emergency']
    ).count()
    
    # Rejected assignments (need reassignment)
    rejected_assignments = ServiceRequest.objects.filter(
        worker_accepted=False
    ).count()
    
    # Worker stats
    total_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    available_workers = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).count()
    
    # Today's stats
    today = datetime.now().date()
    today_requests = ServiceRequest.objects.filter(
        created_at__date=today
    ).count()
    today_completed = ServiceRequest.objects.filter(
        work_completed_at__date=today
    ).count()
    
    # Revenue stats (this week)
    week_start = datetime.now() - timedelta(days=7)
    weekly_revenue = ServiceRequest.objects.filter(
        status='completed',
        work_completed_at__gte=week_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Recent activities
    recent_requests = ServiceRequest.objects.order_by('-created_at')[:5]
    recent_requests_data = ServiceRequestListSerializer(recent_requests, many=True).data
    
    return Response({
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'assigned_requests': assigned_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'urgent_pending': urgent_pending,
        'rejected_assignments': rejected_assignments,
        'total_workers': total_workers,
        'available_workers': available_workers,
        'today_requests': today_requests,
        'today_completed': today_completed,
        'weekly_revenue': str(weekly_revenue),
        'recent_requests': recent_requests_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_available_workers(request):
    """
    Get available workers for assignment
    Filter by category: ?category=5
    Filter by city: ?city=Khartoum
    """
    queryset = WorkerProfile.objects.filter(
        verification_status='verified'
    ).select_related('user').prefetch_related('categories')
    
    # Filter by availability
    availability_filter = request.GET.get('availability', 'available')
    if availability_filter != 'all':
        queryset = queryset.filter(availability=availability_filter)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(categories__id=category_id)
    
    # Filter by city
    city_filter = request.GET.get('city')
    if city_filter:
        queryset = queryset.filter(city__icontains=city_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Annotate with current assignments
    queryset = queryset.annotate(
        current_assignments=Count(
            'assigned_service_requests',
            filter=Q(assigned_service_requests__status='in_progress')
        )
    )
    
    workers = queryset.order_by('current_assignments', '-completed_jobs')[:20]
    
    workers_data = [{
        'id': w.id,
        'name': w.user.get_full_name(),
        'email': w.user.email,
        'phone': w.user.phone_number,
        'availability': w.availability,
        'hourly_rate': str(w.hourly_rate) if w.hourly_rate else None,
        'completed_jobs': w.completed_jobs,
        'city': w.city,
        'current_assignments': w.current_assignments,
        'categories': [{'id': c.id, 'name': c.name} for c in w.categories.all()]
    } for w in workers]
    
    return Response({
        'count': len(workers_data),
        'workers': workers_data
    })
