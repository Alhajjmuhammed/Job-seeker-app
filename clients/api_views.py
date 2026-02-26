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
            # Count available workers in this category
            available_workers = WorkerProfile.objects.filter(
                categories=category,
                availability='available',
                status='approved'
            ).count()
            
            # Get completed projects in this category
            completed_projects = JobRequest.objects.filter(
                category=category,
                status='completed'
            ).count()
            
            # Get average completion days
            avg_days = JobRequest.objects.filter(
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_service(request, category_id):
    """Request a service - admin will assign worker"""
    try:
        category = Category.objects.get(id=category_id)
        
        # Validate request data
        title = request.data.get('title')
        description = request.data.get('description')
        budget = request.data.get('budget')
        location = request.data.get('location')
        deadline = request.data.get('deadline')
        workers_needed = int(request.data.get('workers_needed', 1))
        
        if not all([title, description, budget, location]):
            return Response({
                'error': 'Missing required fields: title, description, budget, location'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create job request
        job_request = JobRequest.objects.create(
            client=request.user,
            category=category,
            title=title,
            description=description,
            budget=budget,
            location=location,
            deadline=deadline,
            workers_needed=workers_needed,
            status='open'  # Will be reviewed by admin
        )
        
        return Response({
            'message': 'Service request submitted successfully! Our team will review and assign a qualified worker within 2-4 hours.',
            'request_id': job_request.id,
            'status': 'pending_assignment'
        })
        
    except Category.DoesNotExist:
        return Response({'error': 'Service category not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({'error': f'Invalid data: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to create service request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CLIENT DASHBOARD & STATISTICS
# ============================================================================


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
        
        # Get total spent (sum of completed jobs budgets)
        total_spent = JobRequest.objects.filter(
            client=request.user,
            status='completed'
        ).aggregate(total=Count('budget'))
        
        return Response({
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
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
            # Count available workers in this category (but don't expose who they are)
            available_workers_count = WorkerProfile.objects.filter(
                categories=category,
                verification_status='verified',
                availability='available'
            ).count()
            
            # Get average completion time and rating for this category
            # (from completed jobs, but still no worker details exposed)
            category_stats = JobRequest.objects.filter(
                category=category,
                status='completed'
            ).aggregate(
                avg_completion_days=Avg('duration_days'),
                avg_budget=Avg('budget'),
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
        
        # Create service request without any worker assignment
        job_data = {
            'client': request.user,
            'category': category,
            'title': request.data.get('title', f"{category.name} Service Request"),
            'description': request.data.get('description', ''),
            'location': request.data.get('location', ''),
            'city': request.data.get('city', ''),
            'budget': request.data.get('budget'),
            'duration_days': request.data.get('duration_days', 1),
            'urgency': request.data.get('urgency', 'medium'),
            'workers_needed': request.data.get('workers_needed', 1),
            'status': 'open'  # Admin will review and assign workers
        }
        
        # Validate required fields
        required_fields = ['description', 'location', 'city']
        for field in required_fields:
            if not request.data.get(field):
                return Response({
                    'error': f'{field.replace("_", " ").title()} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the service request
        job_request = JobRequest.objects.create(**job_data)
        
        # TODO: Send notification to admin about new service request
        # notify_admin_new_service_request(job_request)
        
        return Response({
            'id': job_request.id,
            'message': f'Your {category.name} service request has been submitted successfully!',
            'details': 'Our team will review your request and assign the most suitable worker. You will be notified once a worker is assigned.',
            'status': 'pending_assignment',
            'estimated_response_time': '2-4 hours'
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
        requests = JobRequest.objects.filter(client=request.user).order_by('-created_at')
        
        requests_data = []
        for job_request in requests:
            # Only show assigned worker basic info, not for selection
            assigned_worker_info = None
            if job_request.assigned_workers.exists():
                worker = job_request.assigned_workers.first()
                assigned_worker_info = {
                    'name': worker.user.get_full_name(),
                    'phone': worker.user.phone_number,
                    # Only basic contact info, no profile browsing
                }
            
            requests_data.append({
                'id': job_request.id,
                'service_name': job_request.category.name if job_request.category else 'General Service',
                'title': job_request.title,
                'description': job_request.description,
                'status': job_request.status,
                'status_display': job_request.get_status_display(),
                'urgency': job_request.urgency,
                'location': job_request.location,
                'budget': str(job_request.budget) if job_request.budget else None,
                'created_at': job_request.created_at.isoformat(),
                'assigned_worker': assigned_worker_info,
                'is_assigned': job_request.assigned_workers.exists(),
                'can_cancel': job_request.status in ['open'],
            })
        
        return Response({'requests': requests_data})
    except Exception as e:
        logger.error(f"Error fetching service requests: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def service_request_detail(request, request_id):
    """Get detailed info about a service request"""
    try:
        job_request = JobRequest.objects.get(id=request_id, client=request.user)
        
        # Basic request details
        request_detail = {
            'id': job_request.id,
            'service_name': job_request.category.name if job_request.category else 'General Service',
            'title': job_request.title,
            'description': job_request.description,
            'status': job_request.status,
            'status_display': job_request.get_status_display(),
            'urgency': job_request.urgency,
            'location': job_request.location,
            'city': job_request.city,
            'budget': str(job_request.budget) if job_request.budget else None,
            'duration_days': job_request.duration_days,
            'created_at': job_request.created_at.isoformat(),
            'updated_at': job_request.updated_at.isoformat(),
        }
        
        # Add assigned worker contact info (if assigned)
        if job_request.assigned_workers.exists():
            worker = job_request.assigned_workers.first()
            request_detail['assigned_worker'] = {
                'name': worker.user.get_full_name(),
                'phone': worker.user.phone_number,
                'email': worker.user.email,
                'assigned_at': job_request.updated_at.isoformat(),
                # No detailed profile info - just contact details
            }
        
        return Response(request_detail)
    except JobRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching service request detail: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch request details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_service_request(request, request_id):
    """Cancel a service request (only if not yet assigned)"""
    try:
        job_request = JobRequest.objects.get(id=request_id, client=request.user)
        
        job_request.status = 'cancelled'
        job_request.save()
        
        return Response({
            'message': 'Service request cancelled successfully'
        })
    except JobRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error cancelling service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to cancel request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# JOB MANAGEMENT (Legacy support for existing jobs)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_jobs(request):
    """Get client's jobs (legacy support)"""
    try:
        jobs = JobRequest.objects.filter(client=request.user).order_by('-created_at')
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'id': job.id,
                'title': job.title,
                'status': job.status,
                'status_display': job.get_status_display(),
                'category': job.category.name if job.category else None,
                'created_at': job.created_at.isoformat(),
                'workers_count': job.assigned_workers.count(),
                'budget': str(job.budget) if job.budget else None,
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
        job = JobRequest.objects.get(id=job_id, client=request.user)
        
        job_detail = {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'status': job.status,
            'status_display': job.get_status_display(),
            'category': job.category.name if job.category else None,
            'location': job.location,
            'city': job.city,
            'budget': str(job.budget) if job.budget else None,
            'duration_days': job.duration_days,
            'created_at': job.created_at.isoformat(),
            'workers_needed': job.workers_needed,
            'assigned_workers_count': job.assigned_workers.count(),
        }
        
        return Response(job_detail)
    except JobRequest.DoesNotExist:
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
