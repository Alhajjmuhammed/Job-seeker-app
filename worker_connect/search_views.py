from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count, F, Value, Case, When, Min, Max
from django.db.models.functions import Coalesce
import math
from jobs.service_request_models import ServiceRequest
from workers.models import WorkerProfile, Category
from clients.models import ClientProfile
from jobs.service_request_serializers import ServiceRequestListSerializer
from workers.serializers import WorkerProfileSerializer

class SearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in kilometers"""
    try:
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        return c * r
    except (ValueError, TypeError):
        return float('inf')

@api_view(['GET'])
@permission_classes([AllowAny])
def general_search(request):
    """
    General search endpoint that returns available search options and basic stats
    """
    try:
        # Get basic statistics
        job_count = ServiceRequest.objects.filter(status__in=['pending', 'assigned']).count()
        worker_count = WorkerProfile.objects.filter(user__is_active=True).count()
        category_count = Category.objects.count()
        
        return Response({
            'message': 'Worker Connect Search API',
            'endpoints': {
                'jobs': '/api/search/jobs/',
                'workers': '/api/search/workers/', 
                'filters': '/api/search/filters/'
            },
            'stats': {
                'active_jobs': job_count,
                'active_workers': worker_count,
                'categories': category_count
            },
            'parameters': {
                'query': 'Search term (optional)',
                'category': 'Category filter (optional)',
                'location': 'Location filter (optional)',
                'radius': 'Search radius in km (default: 50)',
                'page': 'Page number (default: 1)',
                'page_size': 'Results per page (default: 20, max: 100)'
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_jobs(request):
    """Advanced job search with multiple filters"""
    try:
        # Get search parameters
        query = request.GET.get('q', '').strip()
        category = request.GET.get('category', '')
        min_budget = request.GET.get('min_budget', '')
        max_budget = request.GET.get('max_budget', '')
        city = request.GET.get('city', '')
        latitude = request.GET.get('latitude', '')
        longitude = request.GET.get('longitude', '')
        radius = request.GET.get('radius', '50')  # Default 50km
        sort_by = request.GET.get('sort_by', 'created_at')
        
        # Start with all active service requests
        jobs = ServiceRequest.objects.filter(status__in=['pending', 'assigned'])
        
        # Text search
        if query:
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # Category filter
        if category:
            jobs = jobs.filter(category__name__iexact=category)
        
        # Price filter
        if min_budget:
            jobs = jobs.filter(total_price__gte=float(min_budget))
        if max_budget:
            jobs = jobs.filter(total_price__lte=float(max_budget))
        
        # Location filter (city)
        if city:
            jobs = jobs.filter(
                Q(location__icontains=city) |
                Q(client__city__icontains=city)
            )
        
        # Location-based filtering (simple approach without GIS)
        jobs_list = list(jobs)
        if latitude and longitude:
            try:
                user_lat = float(latitude)
                user_lon = float(longitude)
                max_distance = float(radius)
                
                filtered_jobs = []
                for job in jobs_list:
                    job_lat = getattr(job, 'latitude', None)
                    job_lon = getattr(job, 'longitude', None)
                    
                    if job_lat and job_lon:
                        distance = haversine_distance(user_lat, user_lon, job_lat, job_lon)
                        if distance <= max_distance:
                            job.distance = distance
                            filtered_jobs.append(job)
                    else:
                        # Include jobs without location data
                        job.distance = None
                        filtered_jobs.append(job)
                
                jobs_list = filtered_jobs
            except ValueError:
                pass
        
        # Convert back to queryset for sorting
        if jobs_list != list(jobs):
            job_ids = [job.id for job in jobs_list]
            jobs = ServiceRequest.objects.filter(id__in=job_ids)
        
        # Sorting
        sort_options = {
            'created_at': '-created_at',
            'budget': '-total_price',
            'title': 'title',
        }
        
        if sort_by in sort_options:
            jobs = jobs.order_by(sort_options[sort_by])
        else:
            jobs = jobs.order_by('-created_at')
        
        # Pagination
        paginator = SearchPagination()
        page = paginator.paginate_queryset(jobs, request)
        
        if page is not None:
            serializer = ServiceRequestListSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response({
                'jobs': serializer.data,
                'total_count': jobs.count(),
                'filters_applied': {
                    'query': query,
                    'category': category,
                    'min_budget': min_budget,
                    'max_budget': max_budget,
                    'city': city,
                    'location_radius': radius if latitude and longitude else None,
                }
            })
        
        serializer = ServiceRequestListSerializer(jobs, many=True, context={'request': request})
        return Response({
            'success': True,
            'jobs': serializer.data,
            'total_count': jobs.count(),
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_workers(request):
    """Advanced worker search with multiple filters"""
    try:
        # Get search parameters
        query = request.GET.get('q', '').strip()
        category = request.GET.get('category', '')
        min_rating = request.GET.get('min_rating', '')
        max_hourly_rate = request.GET.get('max_hourly_rate', '')
        city = request.GET.get('city', '')
        latitude = request.GET.get('latitude', '')
        longitude = request.GET.get('longitude', '')
        radius = request.GET.get('radius', '50')
        availability = request.GET.get('availability', '')
        sort_by = request.GET.get('sort_by', 'average_rating')
        
        # Start with verified workers
        workers = WorkerProfile.objects.filter(
            verification_status='verified',
            user__is_active=True
        ).select_related('user')
        
        # Text search
        if query:
            workers = workers.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(bio__icontains=query) |
                Q(skills__name__icontains=query)
            ).distinct()
        
        # Category filter
        if category:
            workers = workers.filter(categories__name__iexact=category)
        
        # Rating filter
        if min_rating:
            workers = workers.filter(average_rating__gte=float(min_rating))
        
        # Hourly rate filter
        if max_hourly_rate:
            workers = workers.filter(
                hourly_rate__lte=float(max_hourly_rate),
                hourly_rate__isnull=False
            )
        
        # Location filter (city)
        if city:
            workers = workers.filter(city__icontains=city)
        
        # Availability filter
        if availability:
            workers = workers.filter(availability=availability)
        
        # Location-based filtering (simple approach)
        workers_list = list(workers)
        if latitude and longitude:
            try:
                user_lat = float(latitude)
                user_lon = float(longitude)
                max_distance = float(radius)
                
                filtered_workers = []
                for worker in workers_list:
                    worker_lat = getattr(worker, 'latitude', None)
                    worker_lon = getattr(worker, 'longitude', None)
                    
                    if worker_lat and worker_lon:
                        distance = haversine_distance(user_lat, user_lon, worker_lat, worker_lon)
                        if distance <= max_distance:
                            worker.distance = distance
                            filtered_workers.append(worker)
                    else:
                        worker.distance = None
                        filtered_workers.append(worker)
                
                workers_list = filtered_workers
            except ValueError:
                pass
        
        # Convert back to queryset for sorting
        if workers_list != list(workers):
            worker_ids = [worker.id for worker in workers_list]
            workers = WorkerProfile.objects.filter(id__in=worker_ids)
        
        # Sorting
        sort_options = {
            'rating': '-average_rating',
            'experience': '-experience_years',
            'rate': 'hourly_rate',
            'name': 'user__first_name',
            'jobs_completed': '-completed_jobs',
        }
        
        if sort_by in sort_options:
            workers = workers.order_by(sort_options[sort_by])
        else:
            workers = workers.order_by('-average_rating')
        
        # Pagination
        paginator = SearchPagination()
        page = paginator.paginate_queryset(workers, request)
        
        if page is not None:
            serializer = WorkerProfileSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response({
                'workers': serializer.data,
                'total_count': workers.count(),
                'filters_applied': {
                    'query': query,
                    'category': category,
                    'min_rating': min_rating,
                    'max_hourly_rate': max_hourly_rate,
                    'city': city,
                    'availability': availability,
                    'location_radius': radius if latitude and longitude else None,
                }
            })
        
        serializer = WorkerProfileSerializer(workers, many=True, context={'request': request})
        return Response({
            'success': True,
            'workers': serializer.data,
            'total_count': workers.count(),
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_filters(request):
    """Get available filter options for search"""
    try:
        # Get categories
        categories = Category.objects.filter(is_active=True).values('id', 'name')
        
        # Get price ranges from existing service requests
        budget_stats = ServiceRequest.objects.filter(
            status__in=['pending', 'assigned', 'in_progress'],
            total_price__isnull=False
        ).aggregate(
            min_budget=Min('total_price'),
            max_budget=Max('total_price'),
            avg_budget=Avg('total_price')
        )
        
        # Get rating ranges
        rating_stats = WorkerProfile.objects.filter(
            verification_status='verified'
        ).aggregate(
            min_rating=Min('average_rating'),
            max_rating=Max('average_rating'),
            avg_rating=Avg('average_rating')
        )
        
        # Get hourly rate ranges
        rate_stats = WorkerProfile.objects.filter(
            verification_status='verified',
            hourly_rate__isnull=False
        ).aggregate(
            min_rate=Min('hourly_rate'),
            max_rate=Max('hourly_rate'),
            avg_rate=Avg('hourly_rate')
        )
        
        # Get popular cities
        popular_cities = WorkerProfile.objects.filter(
            city__isnull=False
        ).values('city').annotate(
            count=Count('city')
        ).order_by('-count')[:10]
        
        return Response({
            'success': True,
            'filters': {
                'categories': list(categories),
                'budget_range': {
                    'min': budget_stats['min_budget'] or 0,
                    'max': budget_stats['max_budget'] or 10000,
                    'average': budget_stats['avg_budget'] or 500,
                },
                'rating_range': {
                    'min': rating_stats['min_rating'] or 0,
                    'max': rating_stats['max_rating'] or 5,
                    'average': rating_stats['avg_rating'] or 4,
                },
                'rate_range': {
                    'min': rate_stats['min_rate'] or 10,
                    'max': rate_stats['max_rate'] or 500,
                    'average': rate_stats['avg_rate'] or 50,
                },
                'popular_cities': [city['city'] for city in popular_cities],
                'availability_options': [
                    {'value': 'available', 'label': 'Available'},
                    {'value': 'busy', 'label': 'Busy'},
                ],
                'sort_options': {
                    'jobs': [
                        {'value': 'created_at', 'label': 'Newest'},
                        {'value': 'budget', 'label': 'Highest Budget'},
                        {'value': 'deadline', 'label': 'Deadline'},
                        {'value': 'title', 'label': 'Title'},
                    ],
                    'workers': [
                        {'value': 'rating', 'label': 'Highest Rated'},
                        {'value': 'experience', 'label': 'Most Experienced'},
                        {'value': 'rate', 'label': 'Lowest Rate'},
                        {'value': 'jobs_completed', 'label': 'Most Jobs Completed'},
                        {'value': 'name', 'label': 'Name'},
                    ]
                }
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)