"""
Search functionality for Worker Connect.

Provides full-text search for jobs and workers with filters.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from jobs.models import JobRequest
from workers.models import WorkerProfile
from jobs.serializers import JobRequestSerializer
from workers.serializers import WorkerProfileSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def search_jobs(request):
    """
    Search jobs with full-text search and filters.
    
    Query params:
        - q: Search query (searches title, description, location)
        - status: Filter by status (open, in_progress, completed)
        - location: Filter by location/city
        - min_budget: Minimum budget
        - max_budget: Maximum budget
        - category: Filter by category
        - sort: Sort by (newest, budget_high, budget_low)
        - page: Page number
        - page_size: Items per page (default: 20, max: 50)
    """
    query = request.query_params.get('q', '').strip()
    job_status = request.query_params.get('status', '')
    location = request.query_params.get('location', '').strip()
    min_budget = request.query_params.get('min_budget')
    max_budget = request.query_params.get('max_budget')
    category = request.query_params.get('category', '').strip()
    sort = request.query_params.get('sort', 'newest')
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 50)
    
    # Base queryset - only open jobs for public search
    jobs = JobRequest.objects.filter(status='open')
    
    # Full-text search if query provided
    if query:
        # Try PostgreSQL full-text search first
        try:
            search_vector = SearchVector('title', weight='A') + \
                           SearchVector('description', weight='B') + \
                           SearchVector('location', weight='C')
            search_query = SearchQuery(query)
            jobs = jobs.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query)
        except Exception:
            # Fallback to simple search for SQLite
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
    
    # Apply filters
    if job_status:
        jobs = jobs.filter(status=job_status)
    
    if location:
        jobs = jobs.filter(
            Q(location__icontains=location) |
            Q(city__icontains=location)
        )
    
    if min_budget:
        try:
            jobs = jobs.filter(budget__gte=float(min_budget))
        except ValueError:
            pass
    
    if max_budget:
        try:
            jobs = jobs.filter(budget__lte=float(max_budget))
        except ValueError:
            pass
    
    if category:
        jobs = jobs.filter(category__iexact=category)
    
    # Sorting
    if sort == 'budget_high':
        jobs = jobs.order_by('-budget', '-created_at')
    elif sort == 'budget_low':
        jobs = jobs.order_by('budget', '-created_at')
    elif query and sort == 'relevance':
        # Sort by search rank if available
        if hasattr(jobs.model, 'rank'):
            jobs = jobs.order_by('-rank', '-created_at')
        else:
            jobs = jobs.order_by('-created_at')
    else:  # newest
        jobs = jobs.order_by('-created_at')
    
    # Pagination
    total_count = jobs.count()
    start = (page - 1) * page_size
    end = start + page_size
    jobs = jobs[start:end]
    
    serializer = JobRequestSerializer(jobs, many=True)
    
    return Response({
        'results': serializer.data,
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_workers(request):
    """
    Search workers with filters (for clients finding workers).
    
    Query params:
        - q: Search query (searches bio, skills, name)
        - skills: Comma-separated list of skills
        - location: Filter by location
        - available_only: Only show available workers (default: true)
        - verified_only: Only show verified workers
        - min_rating: Minimum rating (1-5)
        - sort: Sort by (rating, experience, newest)
        - page: Page number
        - page_size: Items per page
    """
    query = request.query_params.get('q', '').strip()
    skills = request.query_params.get('skills', '').strip()
    location = request.query_params.get('location', '').strip()
    available_only = request.query_params.get('available_only', 'true').lower() == 'true'
    verified_only = request.query_params.get('verified_only', 'false').lower() == 'true'
    min_rating = request.query_params.get('min_rating')
    sort = request.query_params.get('sort', 'rating')
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 50)
    
    # Base queryset
    workers = WorkerProfile.objects.select_related('user').filter(
        user__is_active=True
    )
    
    # Availability filter
    if available_only:
        workers = workers.filter(is_available=True)
    
    # Verified filter
    if verified_only:
        workers = workers.filter(is_verified=True)
    
    # Search query
    if query:
        workers = workers.filter(
            Q(bio__icontains=query) |
            Q(skills__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )
    
    # Skills filter
    if skills:
        skill_list = [s.strip() for s in skills.split(',') if s.strip()]
        for skill in skill_list:
            workers = workers.filter(skills__icontains=skill)
    
    # Location filter
    if location:
        workers = workers.filter(
            Q(location__icontains=location) |
            Q(city__icontains=location)
        )
    
    # Rating filter
    if min_rating:
        try:
            workers = workers.filter(rating__gte=float(min_rating))
        except ValueError:
            pass
    
    # Sorting
    if sort == 'experience':
        workers = workers.order_by('-years_of_experience', '-rating')
    elif sort == 'newest':
        workers = workers.order_by('-user__date_joined')
    else:  # rating (default)
        workers = workers.order_by('-rating', '-total_reviews')
    
    # Pagination
    total_count = workers.count()
    start = (page - 1) * page_size
    end = start + page_size
    workers = workers[start:end]
    
    serializer = WorkerProfileSerializer(workers, many=True)
    
    return Response({
        'results': serializer.data,
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def search_suggestions(request):
    """
    Get search suggestions/autocomplete for jobs.
    
    Query params:
        - q: Partial search query
        - type: 'jobs' or 'locations' (default: jobs)
    """
    query = request.query_params.get('q', '').strip()
    search_type = request.query_params.get('type', 'jobs')
    
    if len(query) < 2:
        return Response({'suggestions': []})
    
    suggestions = []
    
    if search_type == 'locations':
        # Get unique locations
        locations = JobRequest.objects.filter(
            Q(location__icontains=query) | Q(city__icontains=query),
            status='open'
        ).values_list('city', flat=True).distinct()[:10]
        suggestions = list(set(locations))
    else:
        # Get job title suggestions
        titles = JobRequest.objects.filter(
            title__icontains=query,
            status='open'
        ).values_list('title', flat=True).distinct()[:10]
        suggestions = list(titles)
    
    return Response({'suggestions': suggestions})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_filter_options(request):
    """
    Get available filter options for search UI.
    """
    # Get unique categories
    categories = JobRequest.objects.values_list(
        'category', flat=True
    ).distinct().order_by('category')
    
    # Get unique locations/cities
    locations = JobRequest.objects.filter(
        status='open'
    ).values_list('city', flat=True).distinct().order_by('city')[:50]
    
    # Budget range
    budget_range = JobRequest.objects.filter(
        status='open', budget__isnull=False
    ).aggregate(
        min_budget=Avg('budget') * 0 if not JobRequest.objects.exists() else None,
        max_budget=Avg('budget') * 2 if not JobRequest.objects.exists() else None,
    )
    
    return Response({
        'categories': [c for c in categories if c],
        'locations': [l for l in locations if l],
        'budget_range': budget_range,
        'statuses': ['open', 'in_progress', 'completed', 'cancelled'],
    })
