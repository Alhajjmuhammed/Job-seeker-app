"""
Skills matching API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.models import JobRequest
from .skills_matching import SkillsMatcher


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_skills(request):
    """
    Match worker skills against job requirements.
    
    Request body:
        {
            "worker_skills": ["plumbing", "electrical", "carpentry"],
            "job_skills": ["plumber needed", "electrical work"]
        }
        
    OR:
        {
            "worker_id": 1,
            "job_id": 1
        }
    """
    worker_skills = request.data.get('worker_skills')
    job_skills = request.data.get('job_skills')
    worker_id = request.data.get('worker_id')
    job_id = request.data.get('job_id')
    
    # If IDs provided, fetch skills from database
    if worker_id:
        worker = get_object_or_404(WorkerProfile, id=worker_id)
        worker_skills = [s.strip() for s in (worker.skills or '').split(',') if s.strip()]
    
    if job_id:
        job = get_object_or_404(JobRequest, id=job_id)
        job_skills = list(SkillsMatcher.extract_skills(f"{job.title} {job.description}"))
    
    if not worker_skills:
        return Response({
            'error': 'worker_skills or worker_id required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not job_skills:
        return Response({
            'error': 'job_skills or job_id required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate match
    result = SkillsMatcher.calculate_skill_match(worker_skills, job_skills)
    
    return Response({
        'match_score': result['score'],
        'exact_matches': result['exact_matches'],
        'related_matches': result['related_matches'],
        'missing_skills': result['missing_skills'],
        'extra_skills': result['extra_skills'],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def find_matching_workers(request, job_id):
    """
    Find workers that match a job's skill requirements.
    
    Query params:
        - min_score: Minimum match score (default: 0.5)
        - limit: Maximum results (default: 20, max: 50)
    """
    job = get_object_or_404(JobRequest, id=job_id)
    
    # Verify user is job owner or admin
    try:
        client = ClientProfile.objects.get(user=request.user)
        if job.client != client and not request.user.is_staff:
            return Response({
                'error': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
    except ClientProfile.DoesNotExist:
        if not request.user.is_staff:
            return Response({
                'error': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
    
    min_score = float(request.query_params.get('min_score', 0.5))
    limit = min(int(request.query_params.get('limit', 20)), 50)
    
    matches = SkillsMatcher.find_matching_workers(job, min_score, limit)
    
    result = []
    for match in matches:
        worker = match['worker']
        result.append({
            'worker': {
                'id': worker.id,
                'name': worker.user.get_full_name() or worker.user.username,
                'skills': worker.skills,
                'hourly_rate': str(worker.hourly_rate) if hasattr(worker, 'hourly_rate') and worker.hourly_rate else None,
            },
            'match_score': match['match']['score'],
            'exact_matches': match['match']['exact_matches'],
            'related_matches': match['match']['related_matches'],
            'missing_skills': match['match']['missing_skills'],
        })
    
    return Response({
        'job': {
            'id': job.id,
            'title': job.title,
        },
        'matches_count': len(result),
        'matches': result,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def find_matching_jobs(request):
    """
    Find jobs matching the authenticated worker's skills.
    
    Query params:
        - min_score: Minimum match score (default: 0.3)
        - limit: Maximum results (default: 20, max: 50)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access this endpoint'
        }, status=status.HTTP_403_FORBIDDEN)
    
    min_score = float(request.query_params.get('min_score', 0.3))
    limit = min(int(request.query_params.get('limit', 20)), 50)
    
    matches = SkillsMatcher.find_matching_jobs(worker, min_score, limit)
    
    result = []
    for match in matches:
        job = match['job']
        result.append({
            'job': {
                'id': job.id,
                'title': job.title,
                'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
                'location': getattr(job, 'location', ''),
            },
            'match_score': match['match']['score'],
            'exact_matches': match['match']['exact_matches'],
            'related_matches': match['match']['related_matches'],
        })
    
    return Response({
        'worker': {
            'id': worker.id,
            'skills': worker.skills,
        },
        'matches_count': len(result),
        'matches': result,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggest_skills(request):
    """
    Suggest additional skills for a worker to add.
    
    Returns skills related to the worker's current skills.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access this endpoint'
        }, status=status.HTTP_403_FORBIDDEN)
    
    current_skills = [s.strip() for s in (worker.skills or '').split(',') if s.strip()]
    
    suggestions = SkillsMatcher.suggest_skills(current_skills)
    
    return Response({
        'current_skills': current_skills,
        'suggested_skills': suggestions,
    })


@api_view(['GET'])
def get_skill_categories(request):
    """
    Get all skill categories and their associated skills.
    
    Public endpoint for reference.
    """
    categories = {}
    for category, skills in SkillsMatcher.SKILL_CATEGORIES.items():
        categories[category] = sorted(skills)
    
    return Response({
        'categories': categories,
        'total_skills': sum(len(s) for s in SkillsMatcher.SKILL_CATEGORIES.values()),
    })
