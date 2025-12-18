from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q
from workers.models import WorkerProfile
from jobs.models import DirectHireRequest, JobApplication
from .serializers import WorkerProfileSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_profile(request):
    """Get worker profile for the logged-in user"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        serializer = WorkerProfileSerializer(profile)
        return Response(serializer.data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_worker_profile(request):
    """Update worker profile"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        serializer = WorkerProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_worker_availability(request):
    """Update worker availability status"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        is_available = request.data.get('is_available')
        
        if is_available is None:
            return Response({'error': 'is_available field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update availability
        profile.availability = 'available' if is_available else 'unavailable'
        profile.save()
        
        serializer = WorkerProfileSerializer(profile)
        return Response(serializer.data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_stats(request):
    """Get worker dashboard stats"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Count direct hire requests (pending)
        pending_requests = DirectHireRequest.objects.filter(
            worker=profile,
            status='pending'
        ).count()
        
        # Count active jobs (accepted direct hire requests)
        active_jobs = DirectHireRequest.objects.filter(
            worker=profile,
            status='accepted'
        ).count()
        
        # Count total applications
        total_applications = JobApplication.objects.filter(
            worker=profile
        ).count()
        
        # Count accepted applications
        accepted_applications = JobApplication.objects.filter(
            worker=profile,
            status='accepted'
        ).count()
        
        stats = {
            'pending_requests': pending_requests,
            'active_jobs': active_jobs,
            'total_applications': total_applications,
            'accepted_applications': accepted_applications,
        }
        
        return Response(stats)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def direct_hire_requests(request):
    """Get direct hire requests for the logged-in worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Get pending direct hire requests
        requests = DirectHireRequest.objects.filter(
            worker=profile,
            status='pending'
        ).select_related('client__user').order_by('-created_at')
        
        # Serialize the requests
        requests_data = []
        for req in requests:
            requests_data.append({
                'id': req.id,
                'client_name': req.client.user.get_full_name(),
                'client_phone': req.client.phone_number,
                'job_description': req.description,
                'budget': str(req.budget),
                'location': req.location,
                'created_at': req.created_at.isoformat(),
                'status': req.status,
            })
        
        return Response(requests_data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
