"""
Recommendation API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.models import JobRequest
from .recommendations import RecommendationEngine


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_job_recommendations(request):
    """
    Get job recommendations for the authenticated worker.
    
    Query params:
        - limit: Maximum number of recommendations (default: 20, max: 50)
        - include_scores: Include detailed scoring breakdown (default: false)
    """
    # Check if user is a worker
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can get job recommendations'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Parse parameters
    limit = min(int(request.query_params.get('limit', 20)), 50)
    include_scores = request.query_params.get('include_scores', '').lower() == 'true'
    
    # Get recommendations
    recommendations = RecommendationEngine.get_recommendations(
        worker_profile,
        limit=limit,
        include_scores=include_scores
    )
    
    # Format response
    jobs_data = []
    for rec in recommendations:
        job = rec['job']
        job_data = {
            'id': job.id,
            'title': job.title,
            'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
            'location': getattr(job, 'location', ''),
            'budget': str(job.budget) if hasattr(job, 'budget') and job.budget else None,
            'created_at': job.created_at.isoformat(),
            'client': {
                'id': job.client.id,
                'name': job.client.user.get_full_name() or job.client.user.username,
            },
            'match_score': rec['score'],
        }
        
        if include_scores and rec['score_details']:
            job_data['score_breakdown'] = rec['score_details']
        
        jobs_data.append(job_data)
    
    return Response({
        'count': len(jobs_data),
        'recommendations': jobs_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_worker_recommendations(request, job_id):
    """
    Get worker recommendations for a specific job (for clients).
    
    Query params:
        - limit: Maximum number of recommendations (default: 20, max: 50)
        - include_scores: Include detailed scoring breakdown (default: false)
    """
    # Check if user is a client
    try:
        client_profile = ClientProfile.objects.get(user=request.user)
    except ClientProfile.DoesNotExist:
        return Response({
            'error': 'Only clients can get worker recommendations'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get the job
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Verify job belongs to this client
    if job.client != client_profile:
        return Response({
            'error': 'You can only get recommendations for your own jobs'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Parse parameters
    limit = min(int(request.query_params.get('limit', 20)), 50)
    include_scores = request.query_params.get('include_scores', '').lower() == 'true'
    
    # Get recommendations
    recommendations = RecommendationEngine.get_worker_recommendations(
        client_profile,
        job,
        limit=limit,
        include_scores=include_scores
    )
    
    # Format response
    workers_data = []
    for rec in recommendations:
        worker = rec['worker']
        worker_data = {
            'id': worker.id,
            'name': worker.user.get_full_name() or worker.user.username,
            'primary_skill': getattr(worker, 'primary_skill', ''),
            'skills': worker.skills if hasattr(worker, 'skills') else '',
            'location': getattr(worker, 'location', ''),
            'hourly_rate': str(worker.hourly_rate) if hasattr(worker, 'hourly_rate') and worker.hourly_rate else None,
            'average_rating': getattr(worker, 'average_rating', None),
            'completed_jobs': getattr(worker, 'completed_jobs_count', 0),
            'match_score': rec['score'],
        }
        
        if include_scores and rec['score_details']:
            worker_data['score_breakdown'] = rec['score_details']
        
        workers_data.append(worker_data)
    
    return Response({
        'job_id': job_id,
        'job_title': job.title,
        'count': len(workers_data),
        'recommendations': workers_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_similar_jobs(request, job_id):
    """
    Get jobs similar to a specific job.
    
    Useful for showing related job opportunities.
    """
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Find similar jobs based on title and description
    similar_jobs = JobRequest.objects.filter(
        status='open'
    ).exclude(
        id=job_id
    )[:20]  # Limit initial queryset
    
    # Score by title word overlap
    job_title_words = set(job.title.lower().split())
    
    scored_jobs = []
    for similar_job in similar_jobs:
        similar_words = set(similar_job.title.lower().split())
        overlap = len(job_title_words & similar_words)
        
        if overlap > 0:
            score = overlap / max(len(job_title_words), len(similar_words))
            scored_jobs.append({
                'job': similar_job,
                'similarity_score': score,
            })
    
    # Sort by similarity
    scored_jobs.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    # Return top 10
    similar_data = []
    for item in scored_jobs[:10]:
        sj = item['job']
        similar_data.append({
            'id': sj.id,
            'title': sj.title,
            'description': sj.description[:150] + '...' if len(sj.description) > 150 else sj.description,
            'location': getattr(sj, 'location', ''),
            'similarity_score': round(item['similarity_score'], 2),
        })
    
    return Response({
        'original_job': {
            'id': job.id,
            'title': job.title,
        },
        'similar_jobs': similar_data,
    })
