from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from jobs.models import DirectHireRequest, JobApplication
from jobs.service_request_models import ServiceRequest
from workers.models import WorkerProfile
from worker_connect.pagination import paginate_queryset
from .serializers import (
    DirectHireRequestSerializer, JobApplicationSerializer,
    JobApplicationCreateSerializer
)
from .service_request_serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer, ServiceRequestCreateSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_direct_hire_requests(request):
    """Get pending direct hire requests for the logged-in worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    requests = DirectHireRequest.objects.filter(
        worker=worker_profile,
        status='pending'
    ).order_by('-created_at')
    
    return paginate_queryset(request, requests, DirectHireRequestSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_direct_hire_request(request, request_id):
    """Accept a direct hire request"""
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
        hire_request = DirectHireRequest.objects.get(id=request_id, worker=worker_profile)

        if hire_request.status != 'pending':
            return Response({'error': 'This request has already been responded to'}, status=status.HTTP_400_BAD_REQUEST)

        hire_request.status = 'accepted'
        hire_request.responded_at = timezone.now()
        hire_request.save()

        # Mirrors worker_accept_direct_hire (the web view) - without this the
        # worker still shows as 'available' after committing to a direct
        # hire booking, which the web flow correctly prevents.
        worker_profile.availability = 'busy'
        worker_profile.save()

        return Response({'message': 'Request accepted successfully'})
    except DirectHireRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_direct_hire_request(request, request_id):
    """Reject a direct hire request"""
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
        hire_request = DirectHireRequest.objects.get(id=request_id, worker=worker_profile)

        if hire_request.status != 'pending':
            return Response({'error': 'This request has already been responded to'}, status=status.HTTP_400_BAD_REQUEST)

        hire_request.status = 'rejected'
        hire_request.responded_at = timezone.now()
        hire_request.save()
        return Response({'message': 'Request rejected successfully'})
    except DirectHireRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_job_listings(request):
    """
    Get available job listings for workers.

    Uses ServiceRequestListSerializer, not the full ServiceRequestSerializer -
    this lists OTHER clients' pending requests to any authenticated user, and
    the full serializer leaks each client's email, admin_notes,
    payment_transaction_id, and payment_screenshot. See browse_jobs() above
    for the same fix and rationale.
    """
    jobs = ServiceRequest.objects.filter(status='pending') \
        .select_related('client', 'category', 'assigned_worker') \
        .order_by('-created_at')
    return paginate_queryset(request, jobs, ServiceRequestListSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_applications(request):
    """Get worker's job applications"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    applications = JobApplication.objects.filter(worker=worker_profile) \
        .select_related('job', 'job__client', 'job__category', 'worker') \
        .order_by('-created_at')
    return paginate_queryset(request, applications, JobApplicationSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_job(request, job_id):
    """
    Apply for a job.

    NOTE: `job_id` here refers to a ServiceRequest (the current admin-mediated
    system), not the legacy JobRequest that JobApplication.job points to.
    Workers don't self-apply to ServiceRequests in this system - admins
    assign workers to them instead (see admin_panel/service_request_views.py
    and workers/assignment_views.py). Creating a JobApplication against a
    ServiceRequest instance would raise a ValueError (wrong FK type), so we
    return a clear, honest response instead of crashing.
    """
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can apply for jobs'}, status=status.HTTP_403_FORBIDDEN)

    try:
        WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if not ServiceRequest.objects.filter(id=job_id).exists():
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'error': 'Direct applications are not supported for this job. '
                 'An admin will review your profile and assign you to matching service requests.'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_stats(request):
    """Get worker statistics"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    stats = {
        'pending_requests': DirectHireRequest.objects.filter(worker=worker_profile, status='pending').count(),
        'active_jobs': DirectHireRequest.objects.filter(worker=worker_profile, status='accepted').count(),
        'total_applications': JobApplication.objects.filter(worker=worker_profile).count(),
        'accepted_applications': JobApplication.objects.filter(worker=worker_profile, status='accepted').count(),
    }
    
    return Response(stats)


# ============ Client Job Management ============

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def client_jobs(request):
    """Get client's posted jobs or create a new job"""
    if request.user.user_type != 'client':
        return Response({'error': 'Only clients can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        # Get client's jobs with optional status filter
        status_filter = request.GET.get('status')
        jobs = ServiceRequest.objects.filter(client=request.user)
        
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        
        jobs = jobs.select_related('category', 'assigned_worker').order_by('-created_at')
        return paginate_queryset(request, jobs, ServiceRequestSerializer)
    
    elif request.method == 'POST':
        # Create new job
        serializer = ServiceRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(client=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def client_job_detail(request, job_id):
    """Get, update, or delete a specific job"""
    try:
        job = ServiceRequest.objects.get(id=job_id, client=request.user)
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        job = ServiceRequest.objects.filter(id=job_id).select_related(
            'category', 'assigned_worker', 'assigned_worker__user'
        ).first()
        serializer = ServiceRequestSerializer(job)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = ServiceRequestCreateSerializer(job, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        job.delete()
        return Response({'message': 'Job deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_job_applications(request, job_id):
    """
    Get applications for a specific job.

    NOTE: job_id refers to a ServiceRequest, which JobApplication.job cannot
    point to (see apply_for_job above) - so there are never any legitimate
    JobApplication rows for a ServiceRequest. Returning an empty list here
    instead of filtering JobApplication by a mismatched id avoids silently
    matching unrelated legacy JobRequest applications that happen to share
    the same numeric id.
    """
    if not ServiceRequest.objects.filter(id=job_id, client=request.user).exists():
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

    return paginate_queryset(request, JobApplication.objects.none(), JobApplicationSerializer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_application(request, application_id):
    """Accept a job application"""
    try:
        application = JobApplication.objects.select_related('job', 'job__client').get(id=application_id)
        
        # Explicit permission check
        if application.job.client != request.user:
            return Response({'error': 'You do not have permission to accept this application'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        application.status = 'accepted'
        application.save(update_fields=['status'])
        
        # Update job status to in_progress
        job = application.job
        if job.status == 'pending':
            job.status = 'in_progress'
            job.save(update_fields=['status'])
        
        return Response({'message': 'Application accepted successfully'})
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_application(request, application_id):
    """Reject a job application"""
    try:
        application = JobApplication.objects.select_related('job', 'job__client').get(id=application_id)
        
        # Explicit permission check
        if application.job.client != request.user:
            return Response({'error': 'You do not have permission to reject this application'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        application.status = 'rejected'
        application.save(update_fields=['status'])
        return Response({'message': 'Application rejected successfully'})
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def browse_jobs(request):
    """
    Browse all open job listings (for workers).

    Uses ServiceRequestListSerializer (not the full ServiceRequestSerializer)
    because this lists OTHER clients' pending requests to any authenticated
    user. The full serializer includes each client's email, admin_notes,
    payment_transaction_id, and payment_screenshot - private/internal data
    that must not be exposed to unrelated users. This matches the pattern
    already used by the equivalent listing endpoints (worker_connect.search_views
    job_search, admin_panel's request list, and clients' own request list).
    """
    jobs = ServiceRequest.objects.filter(status='pending') \
        .select_related('client', 'category', 'assigned_worker') \
        .order_by('-created_at')

    # Optional filters
    category = request.GET.get('category')
    if category:
        jobs = jobs.filter(category_id=category)

    city = request.GET.get('city')
    if city:
        jobs = jobs.filter(city__icontains=city)

    return paginate_queryset(request, jobs, ServiceRequestListSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    """Get detailed information about a specific job"""
    try:
        job = ServiceRequest.objects.select_related('client', 'category', 'assigned_worker', 'assigned_worker__user') \
            .get(id=job_id)

        # The full serializer includes private data (client phone/email,
        # payment info, admin notes) - restrict to the owning client, an
        # assigned worker on this job, or staff. Without this, any
        # authenticated user could enumerate job IDs and read any other
        # client's private/financial data.
        user = request.user
        is_owner = job.client_id == user.id
        is_assigned_worker = hasattr(user, 'worker_profile') and (
            job.assignments.filter(worker=user.worker_profile).exists()
            or job.assigned_worker_id == getattr(user.worker_profile, 'id', None)
        )
        if not (user.is_staff or is_owner or is_assigned_worker):
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServiceRequestSerializer(job)
        return Response(serializer.data)
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
