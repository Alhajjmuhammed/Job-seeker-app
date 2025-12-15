from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from jobs.models import DirectHireRequest, JobRequest, JobApplication
from workers.models import WorkerProfile
from .serializers import DirectHireRequestSerializer, JobRequestSerializer, JobApplicationSerializer


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
