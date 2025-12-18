from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count
from jobs.models import DirectHireRequest, JobRequest, JobApplication
from workers.models import WorkerProfile
from .serializers import (
    DirectHireRequestSerializer, JobRequestSerializer, JobApplicationSerializer,
    JobRequestCreateSerializer, JobApplicationCreateSerializer
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
    
    serializer = DirectHireRequestSerializer(requests, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_direct_hire_request(request, request_id):
    """Accept a direct hire request"""
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
        hire_request = DirectHireRequest.objects.get(id=request_id, worker=worker_profile)
        hire_request.status = 'accepted'
        hire_request.save()
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
        hire_request.status = 'rejected'
        hire_request.save()
        return Response({'message': 'Request rejected successfully'})
    except DirectHireRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_job_listings(request):
    """Get available job listings for workers"""
    jobs = JobRequest.objects.filter(status='open').order_by('-created_at')
    serializer = JobRequestSerializer(jobs, many=True)
    return Response(serializer.data)


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
    
    applications = JobApplication.objects.filter(worker=worker_profile).order_by('-created_at')
    serializer = JobApplicationSerializer(applications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_job(request, job_id):
    """Apply for a job"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can apply for jobs'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        job = JobRequest.objects.get(id=job_id)
        
        # Check if already applied
        if JobApplication.objects.filter(worker=worker_profile, job=job).exists():
            return Response({'error': 'Already applied for this job'}, status=status.HTTP_400_BAD_REQUEST)
        
        application = JobApplication.objects.create(
            worker=worker_profile,
            job=job,
            proposed_rate=request.data.get('proposed_rate'),
            cover_letter=request.data.get('cover_letter', '')
        )
        
        serializer = JobApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


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
        jobs = JobRequest.objects.filter(client=request.user)
        
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        
        jobs = jobs.annotate(application_count=Count('applications')).order_by('-created_at')
        serializer = JobRequestSerializer(jobs, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Create new job
        serializer = JobRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(client=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def client_job_detail(request, job_id):
    """Get, update, or delete a specific job"""
    try:
        job = JobRequest.objects.get(id=job_id, client=request.user)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        job_with_count = JobRequest.objects.filter(id=job_id).annotate(
            application_count=Count('applications')
        ).first()
        serializer = JobRequestSerializer(job_with_count)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = JobRequestCreateSerializer(job, data=request.data, partial=True)
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
    """Get applications for a specific job"""
    try:
        job = JobRequest.objects.get(id=job_id, client=request.user)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    applications = JobApplication.objects.filter(job=job).order_by('-created_at')
    serializer = JobApplicationSerializer(applications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_application(request, application_id):
    """Accept a job application"""
    try:
        application = JobApplication.objects.get(id=application_id, job__client=request.user)
        application.status = 'accepted'
        application.save()
        
        # Update job status to in_progress
        job = application.job
        if job.status == 'open':
            job.status = 'in_progress'
            job.save()
        
        return Response({'message': 'Application accepted successfully'})
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_application(request, application_id):
    """Reject a job application"""
    try:
        application = JobApplication.objects.get(id=application_id, job__client=request.user)
        application.status = 'rejected'
        application.save()
        return Response({'message': 'Application rejected successfully'})
    except JobApplication.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def browse_jobs(request):
    """Browse all open job listings (for workers)"""
    jobs = JobRequest.objects.filter(status='open').annotate(
        application_count=Count('applications')
    ).order_by('-created_at')
    
    # Optional filters
    category = request.GET.get('category')
    if category:
        jobs = jobs.filter(category_id=category)
    
    city = request.GET.get('city')
    if city:
        jobs = jobs.filter(city__icontains=city)
    
    serializer = JobRequestSerializer(jobs, many=True)
    return Response(serializer.data)
