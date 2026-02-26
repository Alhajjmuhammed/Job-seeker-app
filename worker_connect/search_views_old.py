from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count, F, Value, Case, When, Min, Max
from django.db.models.functions import Coalesce
import math
from jobs.models import JobRequest, JobCategory
from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.serializers import JobRequestSerializer
from workers.serializers import WorkerProfileSerializer

class SearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([AllowAny])
def search_jobs(request):
    """Advanced job search with multiple filters"""
    jobs = JobRequest.objects.filter(status__in=['open', 'in_progress'])
    
    # Text search
    query = request.GET.get('q', '').strip()
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(required_skills__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Category filter
    category = request.GET.get('category')
    if category:
        jobs = jobs.filter(category_id=category)
    
    # Location-based search
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    radius = request.GET.get('radius', '50')  # Default 50km radius
    
    if latitude and longitude:
        try:
            user_location = Point(float(longitude), float(latitude), srid=4326)
            distance_km = float(radius)
            jobs = jobs.filter(
                location__distance_lt=(user_location, Distance(km=distance_km))
            )
            # Add distance annotation
            jobs = jobs.annotate(
                distance=Distance('location', user_location)
            )
        except (ValueError, TypeError):
            pass
    
    # Budget/Price range filter
    min_budget = request.GET.get('min_budget')
    max_budget = request.GET.get('max_budget')
    
    if min_budget:
        try:
            jobs = jobs.filter(budget__gte=float(min_budget))
        except (ValueError, TypeError):
            pass
    
    if max_budget:
        try:
            jobs = jobs.filter(budget__lte=float(max_budget))
        except (ValueError, TypeError):
            pass
    
    # Job type filter
    job_type = request.GET.get('job_type')
    if job_type in ['fixed_price', 'hourly']:
        jobs = jobs.filter(job_type=job_type)
    
    # Urgency filter
    urgency = request.GET.get('urgency')
    if urgency in ['low', 'medium', 'high', 'urgent']:
        jobs = jobs.filter(urgency=urgency)
    
    # Date posted filter
    date_posted = request.GET.get('date_posted')
    if date_posted:
        from django.utils import timezone
        from datetime import timedelta
        
        if date_posted == 'today':
            jobs = jobs.filter(created_at__date=timezone.now().date())
        elif date_posted == 'week':
            jobs = jobs.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif date_posted == 'month':
            jobs = jobs.filter(created_at__gte=timezone.now() - timedelta(days=30))
    
    # Exclude jobs user already applied to (if authenticated)
    if request.user.is_authenticated:
        applied_jobs = request.user.job_applications.values_list('job_request_id', flat=True)
        jobs = jobs.exclude(id__in=applied_jobs)
    
    # Sorting
    sort_by = request.GET.get('sort', 'created_at')
    sort_order = request.GET.get('order', 'desc')
    
    sort_fields = {
        'created_at': 'created_at',
        'budget': 'budget',
        'urgency': 'urgency',
        'distance': 'distance' if 'distance' in [f.name for f in jobs.model._meta.fields if hasattr(f, 'name')] else 'created_at'
    }
    
    sort_field = sort_fields.get(sort_by, 'created_at')
    if sort_order == 'desc':
        sort_field = f'-{sort_field}'
    
    jobs = jobs.order_by(sort_field)
    
    # Pagination
    paginator = SearchPagination()
    page = paginator.paginate_queryset(jobs, request)
    
    if page is not None:
        serializer = JobRequestSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response({
            'results': serializer.data,
            'filters': {
                'query': query,
                'category': category,
                'min_budget': min_budget,
                'max_budget': max_budget,
                'job_type': job_type,
                'urgency': urgency,
                'date_posted': date_posted,
                'sort': sort_by,
                'order': sort_order
            }
        })
    
    serializer = JobRequestSerializer(jobs, many=True, context={'request': request})
    return Response({
        'success': True,
        'jobs': serializer.data,
        'count': jobs.count()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def search_workers(request):
    """Advanced worker search with multiple filters"""
    workers = WorkerProfile.objects.filter(
        is_available=True,
        verification_status='verified'
    ).annotate(
        avg_rating=Avg('user__received_reviews__rating'),
        total_jobs=Count('user__assigned_jobs', filter=Q(user__assigned_jobs__status='completed')),
        total_reviews=Count('user__received_reviews')
    )
    
    # Text search
    query = request.GET.get('q', '').strip()
    if query:
        workers = workers.filter(
            Q(bio__icontains=query) |
            Q(skills__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specializations__name__icontains=query)
        )
    
    # Skills filter
    skills = request.GET.get('skills', '').strip()
    if skills:
        skill_list = [skill.strip() for skill in skills.split(',') if skill.strip()]
        for skill in skill_list:
            workers = workers.filter(skills__icontains=skill)
    
    # Location-based search
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')
    radius = request.GET.get('radius', '50')  # Default 50km radius
    
    if latitude and longitude:
        try:
            user_location = Point(float(longitude), float(latitude), srid=4326)
            distance_km = float(radius)
            workers = workers.filter(
                location__distance_lt=(user_location, Distance(km=distance_km))
            )
            workers = workers.annotate(
                distance=Distance('location', user_location)
            )
        except (ValueError, TypeError):
            pass
    
    # Hourly rate filter
    min_rate = request.GET.get('min_rate')
    max_rate = request.GET.get('max_rate')
    
    if min_rate:
        try:
            workers = workers.filter(hourly_rate__gte=float(min_rate))
        except (ValueError, TypeError):
            pass
    
    if max_rate:
        try:
            workers = workers.filter(hourly_rate__lte=float(max_rate))
        except (ValueError, TypeError):
            pass
    
    # Experience level filter
    experience_level = request.GET.get('experience_level')
    if experience_level in ['beginner', 'intermediate', 'expert']:
        workers = workers.filter(experience_level=experience_level)
    
    # Availability filter
    availability = request.GET.get('availability')
    if availability == 'immediate':
        workers = workers.filter(is_available=True)
    elif availability == 'this_week':
        # Custom logic for availability this week
        pass
    
    # Minimum rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating:
        try:
            workers = workers.filter(avg_rating__gte=float(min_rating))
        except (ValueError, TypeError):
            pass
    
    # Verification status
    verified_only = request.GET.get('verified_only', '').lower() == 'true'
    if verified_only:
        workers = workers.filter(verification_status='verified')
    
    # Languages filter
    languages = request.GET.get('languages', '').strip()
    if languages:
        lang_list = [lang.strip() for lang in languages.split(',') if lang.strip()]
        for lang in lang_list:
            workers = workers.filter(languages__icontains=lang)
    
    # Sorting
    sort_by = request.GET.get('sort', 'avg_rating')
    sort_order = request.GET.get('order', 'desc')
    
    sort_fields = {
        'rating': 'avg_rating',
        'hourly_rate': 'hourly_rate',
        'experience': 'years_experience',
        'jobs_completed': 'total_jobs',
        'distance': 'distance' if 'distance' in [f.name for f in workers.model._meta.fields if hasattr(f, 'name')] else 'avg_rating'
    }
    
    sort_field = sort_fields.get(sort_by, 'avg_rating')
    if sort_order == 'desc':
        sort_field = f'-{sort_field}'
    
    workers = workers.order_by(sort_field)
    
    # Pagination
    paginator = SearchPagination()
    page = paginator.paginate_queryset(workers, request)
    
    if page is not None:
        serializer = WorkerProfileSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response({
            'results': serializer.data,
            'filters': {
                'query': query,
                'skills': skills,
                'min_rate': min_rate,
                'max_rate': max_rate,
                'experience_level': experience_level,
                'min_rating': min_rating,
                'verified_only': verified_only,
                'languages': languages,
                'sort': sort_by,
                'order': sort_order
            }
        })
    
    serializer = WorkerProfileSerializer(workers, many=True, context={'request': request})
    return Response({
        'success': True,
        'workers': serializer.data,
        'count': workers.count()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def search_filters(request):
    """Get available search filters and their options"""
    
    # Get categories
    categories = JobCategory.objects.all().values('id', 'name')
    
    # Get price ranges (based on existing jobs)
    price_stats = JobRequest.objects.aggregate(
        min_budget=Min('budget'),
        max_budget=Max('budget'),
        avg_budget=Avg('budget')
    )
    
    # Get available skills (from workers)
    skills = WorkerProfile.objects.exclude(
        skills__isnull=True
    ).exclude(
        skills__exact=''
    ).values_list('skills', flat=True)
    
    # Parse and deduplicate skills
    all_skills = set()
    for skill_text in skills:
        if skill_text:
            skill_list = [s.strip() for s in skill_text.split(',')]
            all_skills.update(skill_list)
    
    popular_skills = sorted(list(all_skills))[:50]  # Top 50 skills
    
    return Response({
        'success': True,
        'filters': {
            'categories': list(categories),
            'job_types': [
                {'value': 'fixed_price', 'label': 'Fixed Price'},
                {'value': 'hourly', 'label': 'Hourly Rate'}
            ],
            'urgency_levels': [
                {'value': 'low', 'label': 'Low'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'high', 'label': 'High'},
                {'value': 'urgent', 'label': 'Urgent'}
            ],
            'experience_levels': [
                {'value': 'beginner', 'label': 'Beginner'},
                {'value': 'intermediate', 'label': 'Intermediate'},
                {'value': 'expert', 'label': 'Expert'}
            ],
            'date_options': [
                {'value': 'today', 'label': 'Today'},
                {'value': 'week', 'label': 'This Week'},
                {'value': 'month', 'label': 'This Month'}
            ],
            'sort_options': {
                'jobs': [
                    {'value': 'created_at', 'label': 'Date Posted'},
                    {'value': 'budget', 'label': 'Budget'},
                    {'value': 'urgency', 'label': 'Urgency'},
                    {'value': 'distance', 'label': 'Distance'}
                ],
                'workers': [
                    {'value': 'rating', 'label': 'Rating'},
                    {'value': 'hourly_rate', 'label': 'Hourly Rate'},
                    {'value': 'experience', 'label': 'Experience'},
                    {'value': 'jobs_completed', 'label': 'Jobs Completed'},
                    {'value': 'distance', 'label': 'Distance'}
                ]
            },
            'price_stats': price_stats,
            'popular_skills': popular_skills
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saved_searches(request):
    """Get user's saved searches"""
    # This would require a SavedSearch model - placeholder for now
    return Response({
        'success': True,
        'saved_searches': [],
        'message': 'Saved searches feature coming soon'
    })