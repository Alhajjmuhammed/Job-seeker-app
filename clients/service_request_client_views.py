"""
Client API Views for Service Requests
Client creates service requests and views their history
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from clients.models import PaymentTransaction

from jobs.service_request_models import ServiceRequest
from jobs.service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    ServiceRequestCreateSerializer, ClientStatsSerializer,
    CategorySerializer
)
from workers.models import Category, WorkerProfile
from workers.proximity import rank_by_distance
from worker_connect.pagination import paginate_queryset

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_categories(request):
    """Get all available service categories"""
    categories = Category.objects.filter(is_active=True).order_by('name')
    serializer = CategorySerializer(categories, many=True)
    return Response({
        'count': categories.count(),
        'categories': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_create_service_request(request):
    """
    Client creates a new service request WITH PAYMENT
    POST /api/client/service-requests/create/
    Body: {
        "category": 1,
        "title": "Need plumber for kitchen sink",
        "description": "Kitchen sink is leaking...",
        "location": "123 Main St, Dar es Salaam",
        "city": "Dar es Salaam",
        "preferred_date": "2026-02-10",
        "preferred_time": "10:00",
        "duration_type": "monthly",  # daily, monthly, 3_months, 6_months, yearly, custom
        "service_start_date": "2026-03-01",  # required for custom
        "service_end_date": "2026-03-15",    # required for custom
        "urgency": "normal",
        "client_notes": "Please bring tools",
        "payment_method": "credit_card",
        "payment_transaction_id": "DEMO-ABC123"
    }
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can create service requests'}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate payment info
    payment_transaction_id = request.data.get('payment_transaction_id')
    payment_method = request.data.get('payment_method')
    
    if not payment_transaction_id or not payment_method:
        return Response({
            'error': 'Payment information required (payment_transaction_id and payment_method)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ServiceRequestCreateSerializer(data=request.data)
    if not serializer.is_valid():
        print(f"Validation errors: {serializer.errors}")
        print(f"Request data: {request.data}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get category to fetch daily rate
    category_id = request.data.get('category')
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check worker availability before creating request
    from workers.models import WorkerProfile
    workers_needed = request.data.get('workers_needed', 1)
    try:
        workers_needed = int(workers_needed)
        workers_needed = max(1, min(100, workers_needed))
    except (ValueError, TypeError):
        workers_needed = 1
    
    available_workers = WorkerProfile.objects.filter(
        categories=category,
        availability='available',
        verification_status='verified'
    ).exclude(
        service_assignments__status__in=['pending', 'accepted', 'in_progress']
    ).distinct().count()
    
    # Determine availability status
    availability_status = 'sufficient' if workers_needed <= available_workers else 'limited'
    availability_message = ''
    
    if workers_needed > available_workers:
        if available_workers == 0:
            availability_message = f'No workers currently available in {category.name}. Your request will be queued.'
            availability_status = 'queued'
        else:
            availability_message = f'Only {available_workers} worker(s) available (requested {workers_needed}). Request will be queued for admin review.'
    else:
        availability_message = f'{available_workers} worker(s) available. Your request will be processed quickly.'
    
    # Create service request with pricing.
    #
    # Deliberately created UNPAID. This path used to mark a booking 'paid'
    # because the caller sent a payment_transaction_id - any string at all -
    # so a client could post a made-up reference and receive the service for
    # free. The other booking endpoint was fixed to verify the reference;
    # this one was missed, which left the bypass wide open on
    # /api/v1/client/service-requests/create/.
    #
    # service_fee is snapshotted here too. It was not passed at all, so it
    # defaulted to zero and the platform earned nothing on anything booked
    # through this endpoint, however the category was priced.
    service_request = serializer.save(
        client=request.user,
        status='pending',
        daily_rate=category.daily_rate,
        service_fee=category.service_fee,
        payment_status='pending',
        payment_method=payment_method,
        payment_transaction_id='',
        paid_at=None,
    )

    # Calculate and save total price
    total_price = service_request.calculate_total_price()
    service_request.save()

    # Only a reference this server issued, to this client, for this amount,
    # and not already spent, is accepted as payment.
    supplied_reference = (payment_transaction_id or '').strip()
    if supplied_reference:
        txn = PaymentTransaction.redeem(
            supplied_reference, request.user, expected_amount=total_price
        )
        if txn is not None:
            txn.consumed_by = service_request
            txn.consumed_at = timezone.now()
            txn.save(update_fields=['consumed_by', 'consumed_at'])
            service_request.payment_status = 'paid'
            service_request.payment_transaction_id = txn.reference
            service_request.paid_at = timezone.now()
            service_request.save(update_fields=[
                'payment_status', 'payment_transaction_id', 'paid_at', 'updated_at',
            ])
        else:
            logger.warning(
                "Rejected unverifiable payment reference %r from user %s",
                supplied_reference[:32], request.user.pk,
            )

    # Apply the client's chosen assignment mode (no-op unless auto_nearest;
    # falls back to admin_choice if it can't auto-assign)
    from .assignment_mode import apply_assignment_mode
    apply_assignment_mode(service_request)
    service_request.refresh_from_db()

    # Update client profile
    if hasattr(request.user, 'client_profile'):
        profile = request.user.client_profile
        profile.total_jobs_posted += 1
        profile.total_spent += service_request.total_price
        profile.save()
    
    # Notify admin about new request
    from worker_connect.notification_service import NotificationService
    NotificationService.notify_admin_new_service_request(service_request)
    
    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Service request created and payment processed successfully. Admin will assign a worker soon.',
        'service_request': response_serializer.data,
        'payment': {
            'status': 'paid',
            'amount': float(service_request.total_price),
            'transaction_id': payment_transaction_id
        },
        'availability': {
            'available_workers': available_workers,
            'availability_status': availability_status,
            'availability_message': availability_message
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_service_requests(request):
    """
    Get all service requests by this client
    Filter: ?status=pending (pending, assigned, in_progress, completed, cancelled)
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    queryset = ServiceRequest.objects.filter(
        client=request.user
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
    
    # Search filter
    search_query = request.GET.get('search')
    if search_query:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(city__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        queryset = queryset.filter(category_id=category_filter)
    
    # Date range
    from_date = request.GET.get('from_date')
    if from_date:
        queryset = queryset.filter(created_at__date__gte=from_date)
    
    to_date = request.GET.get('to_date')
    if to_date:
        queryset = queryset.filter(created_at__date__lte=to_date)
    
    return paginate_queryset(request, queryset, ServiceRequestListSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_service_request_detail(request, pk):
    """Get detailed view of a service request"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    serializer = ServiceRequestSerializer(service_request)
    
    # Time logs belong to this request, so show whatever has been recorded.
    # This was gated on the legacy assigned_worker field, which the real
    # multi-worker assignment flow never populates - so the client never saw
    # any clock in/out history at all.
    from jobs.service_request_serializers import TimeTrackingSerializer
    time_logs = service_request.time_logs.all()
    time_logs_data = TimeTrackingSerializer(time_logs, many=True).data
    
    return Response({
        'service_request': serializer.data,
        'time_logs': time_logs_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_pending_requests(request):
    """Get client's pending service requests (waiting for admin assignment)"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    queryset = ServiceRequest.objects.filter(
        client=request.user,
        status='pending'
    ).select_related('category').order_by('-created_at')
    
    serializer = ServiceRequestListSerializer(queryset, many=True, context={'request': request})
    return Response({
        'count': queryset.count(),
        'pending_requests': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_in_progress_requests(request):
    """Get client's in-progress service requests"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    queryset = ServiceRequest.objects.filter(
        client=request.user,
        status__in=['assigned', 'in_progress']
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
    
    serializer = ServiceRequestListSerializer(queryset, many=True, context={'request': request})
    return Response({
        'count': queryset.count(),
        'in_progress_requests': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_completed_requests(request):
    """Get client's completed service requests (history)"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    queryset = ServiceRequest.objects.filter(
        client=request.user,
        status='completed'
    ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-work_completed_at')
    
    return paginate_queryset(request, queryset, ServiceRequestListSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_cancel_request(request, pk):
    """
    Client cancels a service request (only if pending or assigned, not in progress)
    POST /api/client/service-requests/{pk}/cancel/
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Can only cancel if not in progress or completed
    if service_request.status in ['in_progress', 'completed']:
        return Response(
            {'error': f'Cannot cancel service request that is {service_request.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if service_request.status == 'cancelled':
        return Response(
            {'error': 'Service request is already cancelled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # cancel() releases every active assignment and frees up each worker's
    # availability, and notifies them - a plain status flip here used to
    # leave assignments/worker availability untouched.
    service_request.cancel()

    serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Service request cancelled',
        'service_request': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_statistics(request):
    """Get client's service request statistics"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    # Total requests
    total_requests = ServiceRequest.objects.filter(client=request.user).count()
    pending_requests = ServiceRequest.objects.filter(client=request.user, status='pending').count()
    in_progress_requests = ServiceRequest.objects.filter(
        client=request.user,
        status__in=['assigned', 'in_progress']
    ).count()
    completed_requests = ServiceRequest.objects.filter(client=request.user, status='completed').count()
    
    # Total spent
    total_spent_data = ServiceRequest.objects.filter(
        client=request.user,
        status='completed'
    ).aggregate(total=Sum('total_amount'))
    total_spent = total_spent_data['total'] or 0
    
    stats_serializer = ClientStatsSerializer(data={
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'total_spent': total_spent
    })
    
    stats_serializer.is_valid()
    return Response(stats_serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def client_update_request(request, pk):
    """
    Client updates service request details (only if still pending)
    PUT /api/client/service-requests/{pk}/update/
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Can only update if pending
    if service_request.status != 'pending':
        return Response(
            {'error': 'Can only update pending service requests'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ServiceRequestCreateSerializer(service_request, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    # If the client changed assignment_mode to auto_nearest on this update
    # (e.g. added their location after initially picking "let admin choose"),
    # actually try to auto-assign now - otherwise the field would silently
    # change with no real effect, same gap the create paths guard against.
    from .assignment_mode import apply_assignment_mode
    apply_assignment_mode(service_request)
    service_request.refresh_from_db()

    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Service request updated',
        'service_request': response_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_rate_service(request, pk):
    """
    Client rates a completed service
    POST /api/v1/client/service-requests/{pk}/rate/
    Body: {
        "rating": 5,
        "review": "Excellent service!"
    }
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can rate services'}, status=status.HTTP_403_FORBIDDEN)
    
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user)
    
    # Can only rate completed services
    if service_request.status != 'completed':
        return Response(
            {'error': 'Can only rate completed services'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already rated
    if service_request.client_rating:
        return Response(
            {'error': 'You have already rated this service'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate rating
    rating = request.data.get('rating')
    if not rating:
        return Response({'error': 'Rating is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return Response(
                {'error': 'Rating must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response({'error': 'Rating must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Update rating
    service_request.client_rating = rating
    service_request.client_review = request.data.get('review', '').strip()
    service_request.save(update_fields=['client_rating', 'client_review'])

    # Roll the rating into the worker's aggregate stats (mirrors
    # clients/api_views.py::rate_service_request). assigned_worker is the
    # LEGACY single-worker field and is never populated by the real
    # multi-worker assignment flow (_create_assignment()) - reading it here
    # always silently no-ops. Rate every worker who actually completed this
    # request via the real assignments relation instead.
    completed_assignments = service_request.assignments.filter(status='completed').select_related('worker')
    for assignment in completed_assignments:
        worker = assignment.worker
        new_total = worker.total_reviews + 1
        worker.average_rating = round(
            ((worker.average_rating * worker.total_reviews) + rating) / new_total, 2
        )
        worker.total_reviews = new_total
        worker.save(update_fields=['average_rating', 'total_reviews'])

    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Thank you for your rating!',
        'service_request': response_serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_browse_workers(request):
    """
    Browse available workers for a category, so the client can pick who they
    want (admin still confirms before it becomes a real assignment).
    Only public-safe fields are returned - no phone/email, matching the
    privacy boundary workers/views.py:worker_public_profile already sets for
    client-facing worker data (the admin-facing equivalent exposes contact
    info; this one must not).

    GET /api/v1/client/browse-workers/?category=5&latitude=-6.8&longitude=39.28
    """
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)

    category_id = request.GET.get('category')
    if not category_id:
        return Response({'error': 'category is required'}, status=status.HTTP_400_BAD_REQUEST)

    workers = WorkerProfile.objects.filter(
        categories__id=category_id,
        verification_status='verified',
        availability='available',
        is_public=True
    ).select_related('user').prefetch_related('categories')

    lat = request.GET.get('latitude')
    lon = request.GET.get('longitude')

    if lat and lon:
        workers = rank_by_distance(list(workers), float(lat), float(lon))
    else:
        workers = list(workers.order_by('-average_rating'))

    workers_data = [{
        'id': w.id,
        'name': w.user.get_full_name(),
        'profile_image': w.profile_image.url if w.profile_image else None,
        'bio': w.bio[:200] if w.bio else '',
        'average_rating': str(w.average_rating),
        'completed_jobs': w.completed_jobs,
        'experience_years': w.experience_years,
        'city': w.city,
        'distance_km': round(w.distance_km, 1) if hasattr(w, 'distance_km') else None,
        'categories': [{'id': c.id, 'name': c.name} for c in w.categories.all()],
    } for w in workers]

    return Response({
        'count': len(workers_data),
        'workers': workers_data
    })
