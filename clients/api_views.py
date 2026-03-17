import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import models, transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import ClientProfile, Favorite, Rating
from workers.models import WorkerProfile, Category
from jobs.service_request_models import ServiceRequest
from worker_connect.pagination import paginate_queryset
from .serializers import (
    ClientProfileSerializer, WorkerSearchSerializer,
    CategorySerializer, FavoriteSerializer, RatingSerializer
)
from jobs.service_request_serializers import (
    ServiceRequestListSerializer, ServiceRequestSerializer
)

logger = logging.getLogger(__name__)


# ============================================================================
# SERVICE CATEGORIES (ONLY) - No direct worker access
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_list(request):
    """Get list of available service categories"""
    try:
        categories = Category.objects.all()
        services = []
        
        for category in categories:
            # Count available workers in this category (exclude those with active assignments)
            available_workers = WorkerProfile.objects.filter(
                categories=category,
                availability='available',
                verification_status='verified'
            ).exclude(
                service_assignments__status__in=['pending', 'accepted', 'in_progress']
            ).distinct().count()
            
            # Get completed projects in this category
            completed_projects = ServiceRequest.objects.filter(
                category=category,
                status='completed'
            ).count()
            
            # Get average completion days
            avg_days = ServiceRequest.objects.filter(
                category=category,
                status='completed'
            ).aggregate(avg=Avg('duration_days'))['avg'] or 0
            
            services.append({
                'id': category.id,
                'name': category.name,
                'description': category.description or f"Professional {category.name} services",
                'icon': getattr(category, 'icon', 'construct'),  # Default icon
                'available_workers': available_workers,
                'completed_projects': completed_projects,
                'avg_completion_days': int(avg_days),
                'is_available': available_workers > 0,
            })
        
        return Response({
            'services': services,
            'message': 'Select a service to request and our team will assign the best worker for you.'
        })
    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch services'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CLIENT DASHBOARD & STATISTICS
# ============================================================================


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_stats(request):
    """Get client dashboard statistics"""
    try:
        from jobs.service_request_models import ServiceRequest
        # Count active service requests (pending, assigned, or in_progress)
        active_jobs = ServiceRequest.objects.filter(
            client=request.user,
            status__in=['pending', 'assigned', 'in_progress']
        ).count()
        
        completed_jobs = ServiceRequest.objects.filter(
            client=request.user,
            status='completed'
        ).count()
        
        # Total spent on completed requests
        from django.db.models import Sum
        total_spent_result = ServiceRequest.objects.filter(
            client=request.user,
            status='completed'
        ).aggregate(total=Sum('total_price'))
        total_spent = float(total_spent_result['total'] or 0)
        
        # Count favorites
        favorites = Favorite.objects.filter(client=request.user).count()
        
        return Response({
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
            'total_spent': total_spent,
            'favorites': favorites,
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


# ============================================================================
# SERVICE-ONLY CLIENT API (No Worker Browsing)
# ============================================================================


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_list(request):
    """Get available services/categories (no worker information exposed)"""
    try:
        categories = Category.objects.filter(is_active=True).order_by('name')
        
        # Add service statistics without exposing worker details
        services_data = []
        for category in categories:
            # Count TRULY available workers: status='available' AND not busy with active assignments
            available_workers_count = WorkerProfile.objects.filter(
                categories=category,
                verification_status='verified',
                availability='available'
            ).exclude(
                # Exclude workers with active assignments
                service_assignments__status__in=['pending', 'accepted', 'in_progress']
            ).distinct().count()
            
            # Get average completion time and price for this category
            category_stats = ServiceRequest.objects.filter(
                category=category,
                status='completed'
            ).aggregate(
                avg_completion_days=Avg('duration_days'),
                avg_budget=Avg('total_price'),
                total_completed=Count('id')
            )
            
            services_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'available_workers': available_workers_count,
                'avg_completion_days': int(category_stats['avg_completion_days'] or 0),
                'avg_budget': category_stats['avg_budget'],
                'completed_projects': category_stats['total_completed'],
                'is_available': available_workers_count > 0
            })
        
        return Response({
            'services': services_data,
            'message': 'Select a service and our team will assign the best available worker for you.'
        })
    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch services'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_service(request, category_id):
    """Request a service - admin will assign worker later"""
    try:
        category = Category.objects.get(id=category_id, is_active=True)
        
        # Validate required fields
        required_fields = ['description', 'location', 'city']
        for field in required_fields:
            if not request.data.get(field):
                return Response({
                    'error': f'{field.replace("_", " ").title()} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get duration and pricing info
        duration_type = request.data.get('duration_type', 'daily')
        daily_rate = category.daily_rate or 0
        duration_days = request.data.get('duration_days', 1)
        
        # NEW: Get number of workers needed
        workers_needed = int(request.data.get('workers_needed', 1))
        if workers_needed < 1:
            workers_needed = 1
        elif workers_needed > 100:
            workers_needed = 100
        
        # Check worker availability in this category
        from workers.models import WorkerProfile
        from jobs.service_request_models import ServiceRequestAssignment
        
        # Count available workers: status='available' AND not busy with active assignments
        available_workers = WorkerProfile.objects.filter(
            categories=category,
            availability='available',
            verification_status='verified'
        ).exclude(
            # Exclude workers with active assignments (pending, accepted, in_progress)
            service_assignments__status__in=['pending', 'accepted', 'in_progress']
        ).distinct().count()
        
        # Prepare availability warning/info
        availability_status = 'sufficient' if workers_needed <= available_workers else 'limited'
        availability_message = ''
        
        if workers_needed > available_workers:
            if available_workers == 0:
                availability_message = f'No workers currently available in {category.name}. Your request will be queued.'
                availability_status = 'queued'
            else:
                availability_message = f'Only {available_workers} worker(s) available (requested {workers_needed}). Request will be queued for admin review.'
        else:
            availability_message = f'{available_workers} worker(s) available. Your request will be processed quickly.'
        
        # Calculate total price: daily_rate × duration_days × workers_needed
        total_price = daily_rate * int(duration_days) * workers_needed
        
        # Handle date/time fields - convert empty strings to None
        preferred_date = request.data.get('preferred_date') or None
        preferred_time = request.data.get('preferred_time') or None
        
        # Create service request without any worker assignment
        service_request = ServiceRequest.objects.create(
            client=request.user,
            category=category,
            title=request.data.get('title', f"{category.name} Service Request"),
            description=request.data.get('description', ''),
            location=request.data.get('location', ''),
            city=request.data.get('city', ''),
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            duration_type=duration_type,
            duration_days=duration_days,
            workers_needed=workers_needed,  # NEW: Store workers needed
            daily_rate=daily_rate,
            total_price=total_price,
            urgency=request.data.get('urgency', 'normal'),
            client_notes=request.data.get('client_notes', ''),
            status='pending',  # Admin will review and assign worker(s)
            # Payment info
            payment_status='paid' if request.data.get('payment_transaction_id') else 'pending',
            payment_method=request.data.get('payment_method', ''),
            payment_transaction_id=request.data.get('payment_transaction_id', ''),
            paid_at=timezone.now() if request.data.get('payment_transaction_id') else None,
        )
        
        # Handle payment screenshot if provided
        if 'payment_screenshot' in request.FILES:
            service_request.payment_screenshot = request.FILES['payment_screenshot']
            service_request.save()
        
        # Handle custom date range - convert empty strings to None
        if duration_type == 'custom':
            service_request.service_start_date = request.data.get('service_start_date') or None
            service_request.service_end_date = request.data.get('service_end_date') or None
            service_request.save()
        
        return Response({
            'id': service_request.id,
            'message': f'Your {category.name} service request has been submitted successfully!',
            'details': f'Our admin will review your payment and assign {workers_needed} suitable worker(s). You will be notified once workers are assigned.' if workers_needed > 1 else 'Our admin will review your payment and assign the most suitable worker. You will be notified once a worker is assigned.',
            'workers_needed': workers_needed,
            'available_workers': available_workers,
            'availability_status': availability_status,
            'availability_message': availability_message,
            'status': 'pending_assignment',
            'payment_status': service_request.payment_status,
            'total_price': float(total_price),
            'has_screenshot': bool(service_request.payment_screenshot),
            'estimated_response_time': '2-4 hours' if availability_status == 'sufficient' else '4-8 hours'
        }, status=status.HTTP_201_CREATED)
        
    except Category.DoesNotExist:
        return Response({'error': 'Service category not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error creating service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to create service request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_service_requests(request):
    """Get client's service requests with assigned worker info (if any)"""
    try:
        queryset = ServiceRequest.objects.filter(
            client=request.user
        ).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')

        # Optional filters
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        category_filter = request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)

        search_query = request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city__icontains=search_query)
            )

        from_date = request.GET.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)

        to_date = request.GET.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)

        return paginate_queryset(request, queryset, ServiceRequestListSerializer)
    except Exception as e:
        logger.error(f"Error fetching service requests: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_request_detail(request, request_id):
    """Get detailed info about a service request"""
    try:
        service_request = ServiceRequest.objects.select_related(
            'category'
        ).prefetch_related(
            'assignments__worker__user'
        ).get(id=request_id, client=request.user)

        serializer = ServiceRequestSerializer(service_request, context={'request': request})

        # Include time logs
        time_logs_data = []
        from jobs.service_request_serializers import TimeTrackingSerializer
        time_logs_data = TimeTrackingSerializer(service_request.time_logs.all(), many=True).data

        return Response({
            'service_request': serializer.data,
            'time_logs': time_logs_data,
        })
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching service request detail: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch request details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_service_request(request, request_id):
    """Cancel a service request (only if pending or assigned, not in progress)"""
    try:
        service_request = ServiceRequest.objects.get(id=request_id, client=request.user)

        if service_request.status == 'in_progress':
            return Response(
                {'error': 'Cannot cancel a request that is already in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if service_request.status in ['completed', 'cancelled']:
            return Response(
                {'error': f'Request is already {service_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_request.status = 'cancelled'
        service_request.save()

        return Response({'message': 'Service request cancelled successfully'})
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error cancelling service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to cancel request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_service_request(request, request_id):
    """Mark a service request as completed (client marks as finished)"""
    try:
        service_request = ServiceRequest.objects.get(id=request_id, client=request.user)

        if service_request.status != 'in_progress':
            return Response(
                {'error': f'Cannot mark as completed. Request status is: {service_request.status}. Only in-progress requests can be marked as finished.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()

        # Notify worker that client has marked work as finished
        try:
            if service_request.assigned_worker:
                from jobs.notifications import NotificationService
                NotificationService.create_notification(
                    recipient=service_request.assigned_worker.user,
                    title=f"✅ Service Marked as Finished",
                    message=f"Client has marked '{service_request.title}' as finished. Great work!",
                    notification_type='job_completed',
                    related_job_id=service_request.id
                )
        except Exception as notify_error:
            logger.warning(f"Failed to send completion notification: {notify_error}")

        return Response({
            'message': 'Service request marked as completed successfully',
            'service_request': {
                'id': service_request.id,
                'status': service_request.status,
                'completed_at': service_request.completed_at.isoformat() if service_request.completed_at else None
            }
        })
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error completing service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to mark service as completed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_service_request(request, request_id):
    """Update a service request (including payment screenshot upload)"""
    try:
        service_request = ServiceRequest.objects.get(id=request_id, client=request.user)

        # Check if we're uploading a payment screenshot
        if 'payment_screenshot' in request.FILES:
            service_request.payment_screenshot = request.FILES['payment_screenshot']
            service_request.save()
            
            return Response({
                'message': 'Payment screenshot uploaded successfully',
                'service_request': {
                    'id': service_request.id,
                    'has_screenshot': True,
                    'payment_verified': service_request.payment_verified
                }
            })
        
        # Otherwise, update other fields
        allowed_fields = ['title', 'description', 'location', 'city', 'preferred_date', 
                         'preferred_time', 'estimated_duration_hours', 'urgency', 'client_notes']
        
        for field in allowed_fields:
            if field in request.data:
                setattr(service_request, field, request.data[field])
        
        service_request.save()
        
        return Response({
            'message': 'Service request updated successfully',
            'service_request': {
                'id': service_request.id,
                'title': service_request.title,
                'status': service_request.status
            }
        })
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update service request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# JOB MANAGEMENT (Legacy support for existing jobs)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_jobs(request):
    """Get client's jobs (legacy support)"""
    try:
        jobs = ServiceRequest.objects.filter(client=request.user).order_by('-created_at')
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'id': job.id,
                'title': job.title,
                'status': job.status,
                'status_display': job.get_status_display(),
                'category': job.category.name if job.category else None,
                'created_at': job.created_at.isoformat(),
                'worker_assigned': job.assigned_worker is not None,
                'total_price': str(job.total_price) if job.total_price else None,
            })
        
        return Response({'jobs': jobs_data})
    except Exception as e:
        logger.error(f"Error fetching client jobs: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch jobs'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_job_detail(request, job_id):
    """Get detailed job information (legacy support)"""
    try:
        job = ServiceRequest.objects.get(id=job_id, client=request.user)
        
        job_detail = {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'status': job.status,
            'status_display': job.get_status_display(),
            'category': job.category.name if job.category else None,
            'location': job.location,
            'city': job.city,
            'total_price': str(job.total_price) if job.total_price else None,
            'duration_days': job.duration_days,
            'created_at': job.created_at.isoformat(),
            'worker_assigned': job.assigned_worker is not None,
            'worker_name': job.assigned_worker.user.get_full_name() if job.assigned_worker else None,
        }
        
        return Response(job_detail)
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching job detail: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch job details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CATEGORIES (For Service Selection)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def categories_list(request):
    """Get categories for service selection"""
    try:
        categories = Category.objects.filter(is_active=True).order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response({'categories': serializer.data})
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch categories'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# FAVORITES
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorites_list(request):
    """Get client's list of favorite workers"""
    try:
        favorites = Favorite.objects.filter(
            client=request.user
        ).select_related('worker', 'worker__user').order_by('-created_at')
        
        # Paginate
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        result = paginate_queryset(favorites, page, page_size)
        
        # Serialize favorites with worker details
        favorites_data = []
        for favorite in result['results']:
            worker = favorite.worker
            worker_data = {
                'id': favorite.id,
                'worker_id': worker.id,
                'worker_name': worker.user.get_full_name(),
                'worker_username': worker.user.username,
                'categories': [cat.name for cat in worker.categories.all()],
                'rating': worker.rating,
                'total_reviews': worker.total_reviews,
                'completed_jobs': worker.completed_jobs,
                'hourly_rate': worker.hourly_rate,
                'daily_rate': worker.daily_rate,
                'availability': worker.availability,
                'bio': worker.bio,
                'city': worker.city,
                'profile_picture': request.build_absolute_uri(worker.profile_picture.url) if worker.profile_picture else None,
                'added_at': favorite.created_at.isoformat(),
            }
            favorites_data.append(worker_data)
        
        return Response({
            'results': favorites_data,
            'count': result['count'],
            'next': result['next'],
            'previous': result['previous'],
        })
    except Exception as e:
        logger.error(f"Error fetching favorites: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch favorites'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, worker_id):
    """Add or remove a worker from favorites"""
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        favorite = Favorite.objects.filter(client=request.user, worker=worker).first()
        
        if favorite:
            # Remove from favorites
            favorite.delete()
            return Response({
                'is_favorite': False,
                'message': f'{worker.user.get_full_name()} removed from favorites'
            })
        else:
            # Add to favorites
            Favorite.objects.create(client=request.user, worker=worker)
            return Response({
                'is_favorite': True,
                'message': f'{worker.user.get_full_name()} added to favorites'
            }, status=status.HTTP_201_CREATED)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error toggling favorite: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update favorites'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
