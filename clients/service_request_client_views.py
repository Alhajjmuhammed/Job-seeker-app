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
from datetime import datetime, timedelta

from jobs.service_request_models import ServiceRequest
from jobs.service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    ServiceRequestCreateSerializer, ClientStatsSerializer,
    CategorySerializer
)
from workers.models import Category
from worker_connect.pagination import paginate_queryset


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
        "location": "123 Main St, Khartoum",
        "city": "Khartoum",
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
    
    # Create service request with pricing
    service_request = serializer.save(
        client=request.user, 
        status='pending',
        daily_rate=category.daily_rate,
        payment_status='paid',
        payment_method=payment_method,
        payment_transaction_id=payment_transaction_id,
        paid_at=datetime.now()
    )
    
    # Calculate and save total price
    service_request.calculate_total_price()
    service_request.save()
    
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
    
    # Get time logs if worker was assigned
    time_logs_data = []
    if service_request.assigned_worker:
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
    
    serializer = ServiceRequestListSerializer(queryset, many=True)
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
    
    serializer = ServiceRequestListSerializer(queryset, many=True)
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
    
    service_request.status = 'cancelled'
    service_request.save()
    
    # Notify worker if assigned
    if service_request.assigned_worker:
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_cancelled(service_request)
    
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
    
    response_serializer = ServiceRequestSerializer(service_request)
    return Response({
        'message': 'Service request updated',
        'service_request': response_serializer.data
    })
