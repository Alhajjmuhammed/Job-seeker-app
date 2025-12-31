"""
Job completion and saved jobs API views.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from jobs.models import JobRequest
from workers.models import WorkerProfile
from clients.models import ClientProfile
from .completion import JobCompletionService
from .saved_jobs import SavedJobsService


# Job Completion Views

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_work(request, job_id):
    """
    Worker submits completed work for review.
    
    Request body:
        {
            "notes": "Optional completion notes"
        }
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can submit work'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    notes = request.data.get('notes', '')
    
    result = JobCompletionService.submit_work(job, worker, notes)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_completion(request, job_id):
    """
    Client approves job completion.
    
    Request body:
        {
            "rating": 5,  // 1-5
            "review": "Great work!"
        }
    """
    try:
        client = ClientProfile.objects.get(user=request.user)
    except ClientProfile.DoesNotExist:
        return Response({
            'error': 'Only clients can approve completion'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    rating = request.data.get('rating')
    review = request.data.get('review', '')
    
    if rating and (rating < 1 or rating > 5):
        return Response({
            'error': 'Rating must be between 1 and 5'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = JobCompletionService.approve_completion(job, client, rating, review)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_revision(request, job_id):
    """
    Client requests revision on submitted work.
    
    Request body:
        {
            "reason": "Please fix the issue with..."
        }
    """
    try:
        client = ClientProfile.objects.get(user=request.user)
    except ClientProfile.DoesNotExist:
        return Response({
            'error': 'Only clients can request revision'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    reason = request.data.get('reason', '')
    
    if not reason:
        return Response({
            'error': 'Reason is required for revision request'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = JobCompletionService.request_revision(job, client, reason)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def open_dispute(request, job_id):
    """
    Open a dispute for a job.
    
    Request body:
        {
            "reason": "Work not as described",
            "details": "Additional details..."
        }
    """
    job = get_object_or_404(JobRequest, id=job_id)
    reason = request.data.get('reason', '')
    details = request.data.get('details', '')
    
    if not reason:
        return Response({
            'error': 'Reason is required for dispute'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = JobCompletionService.open_dispute(job, request.user, reason, details)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def resolve_dispute(request, job_id):
    """
    Admin resolves a dispute.
    
    Request body:
        {
            "resolution": "complete" | "cancel" | "partial_refund",
            "favor": "client" | "worker" | "split",
            "notes": "Admin notes"
        }
    """
    job = get_object_or_404(JobRequest, id=job_id)
    resolution = request.data.get('resolution')
    favor = request.data.get('favor')
    notes = request.data.get('notes', '')
    
    if resolution not in ['complete', 'cancel', 'partial_refund']:
        return Response({
            'error': 'Invalid resolution'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if favor not in ['client', 'worker', 'split']:
        return Response({
            'error': 'Invalid favor value'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = JobCompletionService.resolve_dispute(job, request.user, resolution, favor, notes)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_job(request, job_id):
    """
    Cancel a job.
    
    Request body:
        {
            "reason": "Optional cancellation reason"
        }
    """
    job = get_object_or_404(JobRequest, id=job_id)
    reason = request.data.get('reason', '')
    
    result = JobCompletionService.cancel_job(job, request.user, reason)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_timeline(request, job_id):
    """
    Get timeline of job events.
    """
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Verify user is involved
    from jobs.models import JobApplication
    is_client = (job.client.user == request.user)
    is_worker = JobApplication.objects.filter(
        job_request=job,
        worker__user=request.user
    ).exists()
    
    if not is_client and not is_worker and not request.user.is_staff:
        return Response({
            'error': 'Not authorized to view this job timeline'
        }, status=status.HTTP_403_FORBIDDEN)
    
    timeline = JobCompletionService.get_job_timeline(job)
    
    return Response({
        'job_id': job.id,
        'job_title': job.title,
        'current_status': job.status,
        'timeline': timeline,
    })


# Saved Jobs Views

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_job(request, job_id):
    """
    Save a job for later viewing.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can save jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    
    result = SavedJobsService.save_job(worker, job)
    
    return Response(result)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unsave_job(request, job_id):
    """
    Remove a job from saved list.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can manage saved jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    
    result = SavedJobsService.unsave_job(worker, job)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_saved_jobs(request):
    """
    Get all saved jobs.
    
    Query params:
        - include_closed: Include closed jobs (default: false)
        - limit: Maximum results (default: 50)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can view saved jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    include_closed = request.query_params.get('include_closed', '').lower() == 'true'
    limit = int(request.query_params.get('limit', 50))
    
    saved_jobs = SavedJobsService.get_saved_jobs(worker, include_closed, limit)
    
    return Response({
        'count': len(saved_jobs),
        'total_saved': SavedJobsService.get_saved_count(worker),
        'saved_jobs': saved_jobs,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def is_job_saved(request, job_id):
    """
    Check if a specific job is saved.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can check saved jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    job = get_object_or_404(JobRequest, id=job_id)
    
    is_saved = SavedJobsService.is_saved(worker, job)
    
    return Response({
        'job_id': job_id,
        'is_saved': is_saved,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_unavailable_saved(request):
    """
    Remove unavailable jobs from saved list.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can manage saved jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    result = SavedJobsService.clear_unavailable(worker)
    
    return Response(result)
