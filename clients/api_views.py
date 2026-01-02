import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import models, transaction
from django.db.models import Q, Count, Avg
from .models import ClientProfile, Favorite, Rating
from workers.models import WorkerProfile, Category
from jobs.models import JobRequest, DirectHireRequest
from worker_connect.pagination import paginate_queryset
from .serializers import (
    ClientProfileSerializer, WorkerSearchSerializer,
    CategorySerializer, FavoriteSerializer, RatingSerializer
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_stats(request):
    """Get client dashboard statistics"""
    try:
        # Get client's jobs
        active_jobs = JobRequest.objects.filter(
            client=request.user,
            status__in=['open', 'in_progress']
        ).count()
        
        completed_jobs = JobRequest.objects.filter(
            client=request.user,
            status='completed'
        ).count()
        
        # Get favorites count
        favorites_count = Favorite.objects.filter(client=request.user).count()
        
        # Get total spent (sum of completed jobs budgets)
        total_spent = JobRequest.objects.filter(
            client=request.user,
            status='completed'
        ).aggregate(total=Count('budget'))
        
        return Response({
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
            'favorites': favorites_count,
            'total_spent': 0,  # TODO: Calculate actual spent when payment system is implemented
        })
    except Exception as e:
        logger.error(f"Error fetching client stats: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch statistics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_profile(request):
    """Get or create client profile"""
    try:
        profile, created = ClientProfile.objects.get_or_create(user=request.user)
        serializer = ClientProfileSerializer(profile)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching client profile: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_client_profile(request):
    """Update client profile"""
    try:
        profile, created = ClientProfile.objects.get_or_create(user=request.user)
        serializer = ClientProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error updating client profile: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_workers(request):
    """Search and filter workers"""
    try:
        workers = WorkerProfile.objects.filter(verification_status='verified') \
            .select_related('user') \
            .prefetch_related('categories', 'skills')
        
        # Search query
        query = request.GET.get('search', '').strip()
        if query:
            workers = workers.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(bio__icontains=query) |
                Q(city__icontains=query)
            )
        
        # Category filter
        category_id = request.GET.get('category')
        if category_id:
            workers = workers.filter(categories__id=category_id)
        
        # Location filter
        location = request.GET.get('location', '').strip()
        if location:
            workers = workers.filter(city__icontains=location)
        
        # Availability filter
        is_available = request.GET.get('is_available')
        if is_available and is_available.lower() == 'true':
            workers = workers.filter(availability='available')
        
        # Minimum rating filter
        min_rating = request.GET.get('min_rating')
        if min_rating:
            try:
                workers = workers.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Sorting
        sort_by = request.GET.get('sort', '-average_rating')
        workers = workers.order_by(sort_by).distinct()
        
        return paginate_queryset(request, workers, WorkerSearchSerializer)
    except Exception as e:
        logger.error(f"Error searching workers: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to search workers'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_detail(request, worker_id):
    """Get detailed worker profile"""
    try:
        worker = WorkerProfile.objects.select_related('user') \
            .prefetch_related('categories', 'skills') \
            .get(id=worker_id, verification_status='verified')
        serializer = WorkerSearchSerializer(worker, context={'request': request})
        
        # Get worker's ratings
        ratings = Rating.objects.filter(worker=worker).order_by('-created_at')[:10]
        ratings_serializer = RatingSerializer(ratings, many=True)
        
        response_data = serializer.data
        response_data['ratings'] = ratings_serializer.data
        
        return Response(response_data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching worker detail: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch worker details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, worker_id):
    """Add or remove worker from favorites"""
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        favorite, created = Favorite.objects.get_or_create(
            client=request.user,
            worker=worker
        )
        
        if not created:
            # Already exists, so remove it
            favorite.delete()
            return Response({'is_favorite': False, 'message': 'Removed from favorites'})
        
        return Response({'is_favorite': True, 'message': 'Added to favorites'})
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error toggling favorite: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update favorites'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorites_list(request):
    """Get client's favorite workers"""
    try:
        favorites = Favorite.objects.filter(client=request.user).select_related('worker')
        return paginate_queryset(request, favorites, FavoriteSerializer)
    except Exception as e:
        logger.error(f"Error fetching favorites: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch favorites'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def categories_list(request):
    """Get all active categories"""
    try:
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch categories'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def featured_workers(request):
    """Get featured workers for client dashboard"""
    try:
        workers = WorkerProfile.objects.filter(
            is_featured=True,
            verification_status='verified',
            availability='available'
        )[:6]
        
        serializer = WorkerSearchSerializer(
            workers,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching featured workers: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch featured workers'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_jobs(request):
    """Get client's posted jobs"""
    try:
        from jobs.serializers import JobRequestSerializer
        
        jobs = JobRequest.objects.filter(client=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        
        return paginate_queryset(request, jobs, JobRequestSerializer)
    except Exception as e:
        logger.error(f"Error fetching client jobs: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch jobs'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_job_detail(request, job_id):
    """Get detailed information about a specific job"""
    try:
        job = JobRequest.objects.get(id=job_id, client=request.user)
        from jobs.serializers import JobRequestSerializer
        serializer = JobRequestSerializer(job)
        return Response(serializer.data)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching job detail: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch job details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_worker(request, worker_id):
    """Rate a worker after job completion"""
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        rating_value = request.data.get('rating')
        review_text = request.data.get('review', '')
        
        if not rating_value or rating_value < 1 or rating_value > 5:
            return Response({'error': 'Rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            # Create or update rating
            rating, created = Rating.objects.update_or_create(
                client=request.user,
                worker=worker,
                defaults={
                    'rating': rating_value,
                    'review': review_text
                }
            )
            
            # Update worker's average rating
            ratings = Rating.objects.filter(worker=worker)
            avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
            worker.average_rating = round(avg_rating, 2) if avg_rating else 0
            worker.save(update_fields=['average_rating'])
        
        return Response({
            'message': 'Rating submitted successfully',
            'rating': {
                'id': rating.id,
                'rating': rating.rating,
                'review': rating.review,
                'created_at': rating.created_at.isoformat()
            }
        })
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error submitting rating: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to submit rating'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
