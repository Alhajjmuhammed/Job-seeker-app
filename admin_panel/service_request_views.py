"""
Admin Views for Service Request Management
Admin assigns workers to service requests
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking, WorkerActivity
from jobs.service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    AdminAssignWorkerSerializer, TimeTrackingSerializer,
    BulkAssignWorkersSerializer, ServiceRequestAssignmentSerializer
)
from workers.models import WorkerProfile, Category
from workers.proximity import rank_by_distance
from worker_connect.pagination import paginate_queryset


def _create_assignment(service_request, worker, admin_user, assignment_number, admin_notes='', activity_description=None):
    """
    Shared logic for turning "this worker is assigned to this request" into
    a real ServiceRequestAssignment: creates the record, flips the worker to
    busy, logs the activity, and notifies the worker. Used by manual assign,
    reassign, bulk-assign, and auto-assign-nearest so this isn't duplicated
    four times.
    """
    # Pricing is per request, not per day: a worker earns the category amount
    # once. Multiplying by duration_days here paid a worker on a monthly
    # booking thirty times over, and paid their agent thirty times the
    # commission, because this value is what both are calculated from.
    individual_payment = service_request.daily_rate
    assignment = ServiceRequestAssignment.objects.create(
        service_request=service_request,
        worker=worker,
        assigned_by=admin_user,
        assignment_number=assignment_number,
        worker_payment=individual_payment,
        admin_notes=admin_notes
    )

    worker.availability = 'busy'
    worker.save()

    WorkerActivity.log_activity(
        worker=worker,
        activity_type='assigned',
        description=activity_description or f'Assigned to: {service_request.title}',
        service_request=service_request,
        location=service_request.location
    )

    from worker_connect.notification_service import NotificationService
    NotificationService.notify_service_assigned(service_request, worker)

    return assignment


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
            verification_status='verified',
            availability='available'
        ).select_related('user')

        # Sort by distance when we know where the request is; otherwise
        # keep today's rating-based order (falls back gracefully for
        # requests/workers with no coordinates).
        if service_request.latitude is not None and service_request.longitude is not None:
            available_workers = rank_by_distance(
                list(available_workers), service_request.latitude, service_request.longitude, limit=10
            )
        else:
            available_workers = list(available_workers.order_by('-average_rating')[:10])

        workers_data = [{
            'id': w.id,
            'name': w.user.get_full_name(),
            'availability': w.availability,
            'completed_jobs': w.completed_jobs,
            'city': w.city,
            'distance_km': round(w.distance_km, 1) if hasattr(w, 'distance_km') else None
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
        
        # Check if worker is available
        if worker.availability != 'available':
            return Response(
                {'error': f'Worker is {worker.availability} and cannot be assigned. Only available workers can be assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if worker has this category
        if service_request.category and not worker.categories.filter(id=service_request.category.id).exists():
            return Response(
                {'error': 'Worker does not have the required category'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check-then-create on workers_needed must be atomic: without the
        # lock, two near-simultaneous assign calls for the last open slot
        # can both read the same "existing_count < workers_needed" result
        # and both create an assignment, over-allocating the request.
        # select_for_update() serializes concurrent admin requests on this
        # ServiceRequest row (real row locking on the production Postgres
        # backend; SQLite ignores FOR UPDATE, so this doesn't add
        # protection under the sqlite dev/test backend, but is correct and
        # effective where it matters).
        with transaction.atomic():
            locked_request = ServiceRequest.objects.select_for_update().get(pk=service_request.pk)

            # Check if worker is already assigned
            existing_assignment = ServiceRequestAssignment.objects.filter(
                service_request=locked_request,
                worker=worker
            ).first()

            if existing_assignment:
                return Response(
                    {'error': 'Worker is already assigned to this request'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if we've reached the maximum workers needed
            existing_assignments_count = ServiceRequestAssignment.objects.filter(
                service_request=locked_request
            ).count()

            if existing_assignments_count >= locked_request.workers_needed:
                return Response(
                    {'error': f'Cannot assign more workers. This request only needs {locked_request.workers_needed} worker(s).'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            assignment = _create_assignment(
                locked_request, worker, request.user,
                assignment_number=existing_assignments_count + 1,
                admin_notes=admin_notes
            )

            # Update service request status if all workers are now assigned
            total_assignments = existing_assignments_count + 1
            if total_assignments >= locked_request.workers_needed:
                locked_request.status = 'assigned'
                locked_request.save()

        serializer = ServiceRequestSerializer(locked_request)
        assignment_serializer = ServiceRequestAssignmentSerializer(assignment)

        return Response({
            'message': 'Worker assigned successfully',
            'service_request': serializer.data,
            'assignment': assignment_serializer.data
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

        # See admin_assign_worker for why this needs to be atomic +
        # row-locked: without it, two concurrent reassign/assign calls for
        # the last open slot can both pass the count check.
        with transaction.atomic():
            locked_request = ServiceRequest.objects.select_for_update().get(pk=service_request.pk)

            # Check if worker is already assigned
            existing_assignment = ServiceRequestAssignment.objects.filter(
                service_request=locked_request,
                worker=worker
            ).first()

            if existing_assignment:
                return Response(
                    {'error': 'Worker is already assigned to this request'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if we've reached the maximum workers needed
            existing_assignments_count = ServiceRequestAssignment.objects.filter(
                service_request=locked_request
            ).count()

            if existing_assignments_count >= locked_request.workers_needed:
                return Response(
                    {'error': f'Cannot assign more workers. This request only needs {locked_request.workers_needed} worker(s).'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            assignment = _create_assignment(
                locked_request, worker, request.user,
                assignment_number=existing_assignments_count + 1,
                admin_notes=admin_notes,
                activity_description=f'Reassigned to: {locked_request.title}'
            )

            # Update service request status if all workers are now assigned
            total_assignments = existing_assignments_count + 1
            if total_assignments >= locked_request.workers_needed:
                locked_request.status = 'assigned'
                locked_request.save()

        serializer = ServiceRequestSerializer(locked_request)
        assignment_serializer = ServiceRequestAssignmentSerializer(assignment)

        return Response({
            'message': 'Worker reassigned successfully',
            'service_request': serializer.data,
            'assignment': assignment_serializer.data
        })

    except WorkerProfile.DoesNotExist:
        return Response(
            {'error': 'Worker not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_bulk_assign_workers(request, pk):
    """
    Admin assigns multiple workers to a service request at once
    POST /api/admin/service-requests/{pk}/bulk-assign/
    Body: {
        "worker_ids": [123, 456, 789],
        "admin_notes": "Best available workers"
    }
    """
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Validate request is not already completed or cancelled
    if service_request.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'Cannot assign workers to {service_request.status} request'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Fast-fail pre-check on a plain (unlocked) read, purely for a quick
    # error response on obviously-oversized requests. Not authoritative -
    # the real capacity check happens under the row lock below, right
    # before creating the assignments.
    existing_count = ServiceRequestAssignment.objects.filter(service_request=service_request).count()

    # Validate data
    serializer = BulkAssignWorkersSerializer(
        data=request.data,
        context={'service_request': service_request}
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    worker_ids = serializer.validated_data['worker_ids']
    admin_notes = serializer.validated_data.get('admin_notes', '')

    # Check total assignments (existing + new) doesn't exceed request needs
    total_after_assignment = existing_count + len(worker_ids)
    if total_after_assignment > service_request.workers_needed:
        remaining_needed = service_request.workers_needed - existing_count
        return Response(
            {
                'error': f'Cannot assign {len(worker_ids)} workers. Request has {existing_count} assigned and only needs {remaining_needed} more worker(s).'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get all workers
        workers = WorkerProfile.objects.filter(id__in=worker_ids)

        # Check category match for workers to assign (read-only, fine
        # outside the lock)
        if service_request.category:
            for worker in workers:
                if not worker.categories.filter(id=service_request.category.id).exists():
                    return Response(
                        {'error': f'Worker "{worker.user.get_full_name()}" does not have the required category'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Re-check "already assigned" + workers_needed capacity, and create
        # the assignments, all under a row lock on the ServiceRequest so a
        # concurrent assign/bulk-assign/auto-assign call on the same request
        # can't sneak in between the count check and the create (see
        # admin_assign_worker for the full explanation).
        with transaction.atomic():
            locked_request = ServiceRequest.objects.select_for_update().get(pk=service_request.pk)

            existing_assignments = ServiceRequestAssignment.objects.filter(service_request=locked_request)
            existing_count = existing_assignments.count()
            already_assigned_ids = set(existing_assignments.values_list('worker_id', flat=True))

            # Filter out workers already assigned
            workers_to_assign = []
            skipped_workers = []

            for worker in workers:
                if worker.id in already_assigned_ids:
                    skipped_workers.append(worker.user.get_full_name())
                else:
                    workers_to_assign.append(worker)

            # If all workers were already assigned, return error
            if not workers_to_assign:
                return Response(
                    {'error': 'All selected workers are already assigned to this request'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_after_assignment = existing_count + len(workers_to_assign)
            if total_after_assignment > locked_request.workers_needed:
                remaining_needed = locked_request.workers_needed - existing_count
                return Response(
                    {
                        'error': f'Cannot assign {len(workers_to_assign)} workers. Request has {existing_count} assigned and only needs {max(remaining_needed, 0)} more worker(s).'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create individual assignments
            assignments_created = []

            for idx, worker in enumerate(workers_to_assign, start=existing_count + 1):
                assignment = _create_assignment(
                    locked_request, worker, request.user,
                    assignment_number=idx,
                    admin_notes=admin_notes,
                    activity_description=f'Assigned to: {locked_request.title} (Worker {idx} of {locked_request.workers_needed})'
                )
                assignments_created.append(assignment)

            # Update service request status only if all workers are now assigned
            total_assignments = existing_count + len(assignments_created)
            if total_assignments >= locked_request.workers_needed:
                locked_request.status = 'assigned'
                locked_request.save()

        # Serialize response
        assignment_serializer = ServiceRequestAssignmentSerializer(assignments_created, many=True)
        request_serializer = ServiceRequestSerializer(locked_request)
        
        # Build response message
        message = f'Successfully assigned {len(assignments_created)} worker(s) to "{service_request.title}"'
        if skipped_workers:
            message += f'. Skipped {len(skipped_workers)} already assigned: {", ".join(skipped_workers)}'
        
        return Response({
            'message': message,
            'service_request': request_serializer.data,
            'assignments': assignment_serializer.data,
            'skipped': skipped_workers,
            'assigned_count': len(assignments_created),
            'skipped_count': len(skipped_workers)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error assigning workers: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_auto_assign_nearest_workers(request, pk):
    """
    Auto-assign the nearest available worker(s) to a service request by GPS
    distance, instead of picking manually.
    POST /api/admin/service-requests/{pk}/auto-assign-nearest/
    Body: {"admin_notes": "Auto-assigned by proximity"} (optional)
    """
    service_request = get_object_or_404(ServiceRequest, pk=pk)

    if service_request.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'Cannot assign worker to {service_request.status} request'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if service_request.latitude is None or service_request.longitude is None:
        return Response(
            {'error': 'This service request has no location coordinates, so nearest-worker matching is not available. Assign manually instead.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    admin_notes = request.data.get('admin_notes', '')

    existing_assignments = ServiceRequestAssignment.objects.filter(service_request=service_request)
    existing_count = existing_assignments.count()
    slots_remaining = service_request.workers_needed - existing_count

    if slots_remaining <= 0:
        return Response(
            {'error': f'This request already has all {service_request.workers_needed} worker(s) assigned.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    already_assigned_ids = set(existing_assignments.values_list('worker_id', flat=True))

    candidates = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).exclude(id__in=already_assigned_ids)

    if service_request.category:
        candidates = candidates.filter(categories=service_request.category)

    nearest = rank_by_distance(
        list(candidates), service_request.latitude, service_request.longitude, limit=slots_remaining
    )

    if not nearest:
        return Response(
            {'error': 'No available workers with a known location match this request right now.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Re-check capacity and create the assignments under a row lock on the
    # ServiceRequest, same as admin_assign_worker - the candidate ranking
    # above is read-only and doesn't need the lock, but the actual
    # count-then-create for the workers_needed cap does, otherwise this can
    # race with a concurrent admin_assign_worker/bulk-assign/auto-assign
    # call on the same request and over-allocate it.
    with transaction.atomic():
        locked_request = ServiceRequest.objects.select_for_update().get(pk=service_request.pk)

        current_assignments = ServiceRequestAssignment.objects.filter(service_request=locked_request)
        current_count = current_assignments.count()
        current_slots_remaining = locked_request.workers_needed - current_count

        if current_slots_remaining <= 0:
            return Response(
                {'error': f'This request already has all {locked_request.workers_needed} worker(s) assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trim to however many slots are actually still open (may be fewer
        # than when `nearest` was computed) and drop anyone who got
        # assigned in the meantime.
        currently_assigned_ids = set(current_assignments.values_list('worker_id', flat=True))
        to_assign = [w for w in nearest if w.id not in currently_assigned_ids][:current_slots_remaining]

        if not to_assign:
            return Response(
                {'error': 'This request already has all worker slots filled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignments_created = []
        for idx, worker in enumerate(to_assign, start=current_count + 1):
            assignment = _create_assignment(
                locked_request, worker, request.user,
                assignment_number=idx,
                admin_notes=admin_notes,
                activity_description=f'Auto-assigned (nearest, {worker.distance_km:.1f} km) to: {locked_request.title}'
            )
            assignments_created.append(assignment)

        total_assignments = current_count + len(assignments_created)
        if total_assignments >= locked_request.workers_needed:
            locked_request.status = 'assigned'
            locked_request.save()

    assignment_serializer = ServiceRequestAssignmentSerializer(assignments_created, many=True)
    request_serializer = ServiceRequestSerializer(locked_request)

    return Response({
        'message': f'Auto-assigned {len(assignments_created)} nearest available worker(s)',
        'service_request': request_serializer.data,
        'assignments': assignment_serializer.data,
        'distances_km': [round(w.distance_km, 1) for w in to_assign]
    }, status=status.HTTP_201_CREATED)


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
    
    # Rejected assignments (need reassignment). The live multi-worker flow
    # records rejections on ServiceRequestAssignment (set by
    # reject_assignment() / the worker-response views), not on the legacy
    # ServiceRequest.worker_accepted field - that field is only ever touched
    # by the unused legacy ServiceRequest.worker_reject() method, so filtering
    # on it here always returned 0 regardless of real rejections.
    rejected_assignments = ServiceRequestAssignment.objects.filter(
        status='rejected'
    ).values('service_request').distinct().count()
    
    # Worker stats
    total_workers = WorkerProfile.objects.filter(verification_status='verified').count()
    available_workers = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).count()
    
    # Today's stats. Use timezone.now() (aware, UTC per settings.TIME_ZONE)
    # rather than naive datetime.now() (server OS local time) - with
    # USE_TZ=True, Django silently coerces a naive datetime by assuming it's
    # already in the current timezone, which is only correct if the server's
    # OS clock happens to be UTC too. Using timezone.now() removes that
    # assumption and matches how the rest of the codebase computes "now".
    today = timezone.now().date()
    today_requests = ServiceRequest.objects.filter(
        created_at__date=today
    ).count()
    today_completed = ServiceRequest.objects.filter(
        work_completed_at__date=today
    ).count()
    
    # Revenue stats (this week). total_amount is the legacy hourly-billing
    # field (a legacy hourly calculation) which the live admin-mediated
    # completion flow (ServiceRequestAssignment.mark_completed) never
    # populates, so it always summed to 0. total_price (daily_rate x
    # duration_days x workers_needed) is what's actually set at request
    # creation and charged to the client - use that instead.
    week_start = timezone.now() - timedelta(days=7)
    weekly_revenue = ServiceRequest.objects.filter(
        status='completed',
        work_completed_at__gte=week_start
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
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
    
    # Annotate with current assignments. 'assigned_service_requests' is the
    # related name of the legacy single-worker ServiceRequest.assigned_worker
    # FK, which the live multi-worker assignment flow (_create_assignment)
    # never populates - it only ever creates ServiceRequestAssignment rows.
    # Counting through that legacy FK always returned 0 for every worker,
    # silently breaking the "sort least-busy first" ordering below.
    # 'service_assignments' is the real related name for
    # ServiceRequestAssignment.worker.
    queryset = queryset.annotate(
        current_assignments=Count(
            'service_assignments',
            filter=Q(service_assignments__status='in_progress')
        )
    )
    
    workers = queryset.order_by('current_assignments', '-completed_jobs')[:20]
    
    workers_data = [{
        'id': w.id,
        'name': w.user.get_full_name(),
        'email': w.user.email,
        'phone': w.user.phone_number,
        'availability': w.availability,
        'completed_jobs': w.completed_jobs,
        'city': w.city,
        'current_assignments': w.current_assignments,
        'categories': [{'id': c.id, 'name': c.name} for c in w.categories.all()]
    } for w in workers]
    
    return Response({
        'count': len(workers_data),
        'workers': workers_data
    })
