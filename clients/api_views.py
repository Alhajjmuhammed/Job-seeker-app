import logging
from datetime import datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import ClientProfile, Favorite, Rating, PaymentTransaction
from .booking_validation import (
    clean_workers_needed, check_text_lengths, check_dates)
from workers.models import WorkerProfile, Category
from workers.file_validators import validate_image_file
from jobs.service_request_models import ServiceRequest
from .assignment_mode import apply_assignment_mode
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
    """Get client dashboard statistics.

    NOTE: this is the endpoint the mobile client dashboard
    (apiService.getClientStatistics() -> GET /v1/clients/stats/) actually
    calls. It previously returned active_jobs/completed_jobs/total_spent/
    favorites, but dashboard.tsx's ClientStats interface reads
    total_requests/active_requests/completed_requests/pending_requests -
    a pure key-name mismatch that meant every stat card silently showed 0.
    Both the legacy keys and the new ones are returned to avoid breaking
    any other caller relying on the old shape.
    """
    try:
        from jobs.service_request_models import ServiceRequest
        total_requests = ServiceRequest.objects.filter(client=request.user).count()

        pending_requests = ServiceRequest.objects.filter(
            client=request.user,
            status='pending'
        ).count()

        # "Active" = accepted work in flight (assigned or in_progress),
        # distinct from "pending" (not yet assigned/accepted).
        active_requests = ServiceRequest.objects.filter(
            client=request.user,
            status__in=['assigned', 'in_progress']
        ).count()

        completed_requests = ServiceRequest.objects.filter(
            client=request.user,
            status='completed'
        ).count()

        # Legacy combined count (pending + assigned + in_progress), kept
        # for any caller still relying on the old 'active_jobs' key.
        active_jobs = pending_requests + active_requests

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
            # Fields consumed by the mobile client dashboard
            'total_requests': total_requests,
            'active_requests': active_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'total_spent': total_spent,
            # Legacy keys, kept for backward compatibility
            'active_jobs': active_jobs,
            'completed_jobs': completed_requests,
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
        
        # Get duration and pricing info. duration_days is ALWAYS derived
        # server-side from duration_type (and, for 'custom', the start/end
        # dates) - it must never be trusted from the client. The mobile app
        # only ever sends duration_type (see request-service.tsx), so
        # trusting a client-supplied duration_days here previously meant it
        # silently defaulted to 1 for every single request regardless of
        # duration_type, undercharging every non-daily booking (monthly,
        # 3/6-month, yearly, custom) down to a single day's rate.
        duration_type = request.data.get('duration_type', 'daily')
        daily_rate = category.daily_rate or 0

        duration_map = {
            'daily': 1,
            'monthly': 30,
            '3_months': 90,
            '6_months': 180,
            'yearly': 365,
        }
        service_start_date = request.data.get('service_start_date') or None
        service_end_date = request.data.get('service_end_date') or None
        if duration_type == 'custom':
            if not service_start_date or not service_end_date:
                return Response({
                    'error': 'service_start_date and service_end_date are required for custom duration'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                start = datetime.strptime(service_start_date, '%Y-%m-%d').date()
                end = datetime.strptime(service_end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid date format for service_start_date/service_end_date. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
            if end < start:
                return Response({
                    'error': 'service_end_date must be after service_start_date'
                }, status=status.HTTP_400_BAD_REQUEST)
            duration_days = (end - start).days + 1
        else:
            duration_days = duration_map.get(duration_type, 1)

        # NEW: Get number of workers needed
        # Nonsense worker counts used to be silently coerced: 0 and -5 became
        # 1, and 100000 was clamped to 100 and priced as a crew of a hundred.
        workers_needed, workers_error = clean_workers_needed(
            request.data.get('workers_needed', 1))
        if workers_error:
            return Response({'error': workers_error},
                            status=status.HTTP_400_BAD_REQUEST)

        # SQLite ignores max_length but PostgreSQL raises, so an over-long
        # title is a 500 in production unless it is caught here.
        text_error = check_text_lengths(request.data)
        if text_error:
            return Response({'error': text_error},
                            status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Price per request: (category amount x workers) + one service fee.
        # Duration is scheduling information and does not affect the price.
        # The quote and the stored record come from the same model method so
        # they can never disagree.
        quote = ServiceRequest.quote(category, workers_needed)
        service_fee = quote['service_fee']
        total_price = quote['total_price']
        
        # Handle date/time fields - convert empty strings to None
        preferred_date = request.data.get('preferred_date') or None
        preferred_time = request.data.get('preferred_time') or None

        # A booking must not start in the past, and the range must run
        # forwards. Both were accepted before.
        date_error = check_dates(service_start_date, service_end_date, preferred_date)
        if date_error:
            return Response({'error': date_error},
                            status=status.HTTP_400_BAD_REQUEST)

        # Optional GPS coordinates for the service location (form data
        # always arrives as strings - must cast, or later distance math
        # blows up with "must be real number, not str")
        try:
            latitude = float(request.data.get('latitude')) if request.data.get('latitude') else None
            longitude = float(request.data.get('longitude')) if request.data.get('longitude') else None
        except (TypeError, ValueError):
            latitude = None
            longitude = None

        # Optional worker the client requested themselves - admin still
        # confirms this before it becomes a real assignment (see
        # ServiceRequest.preferred_worker)
        preferred_worker = None
        preferred_worker_id = request.data.get('preferred_worker')
        if preferred_worker_id:
            try:
                preferred_worker = WorkerProfile.objects.get(id=preferred_worker_id)
            except WorkerProfile.DoesNotExist:
                return Response({'error': 'Preferred worker not found'}, status=status.HTTP_404_NOT_FOUND)
            if not preferred_worker.categories.filter(id=category.id).exists():
                return Response({'error': "This worker doesn't offer the requested category"}, status=status.HTTP_400_BAD_REQUEST)

        # How the client wants their worker selected: admin picks (default),
        # client already picked one above (preferred_worker), or auto-assign
        # the nearest available worker right now (see assignment_mode.py)
        assignment_mode = request.data.get('assignment_mode', 'admin_choice')
        if assignment_mode not in dict(ServiceRequest.ASSIGNMENT_MODE_CHOICES):
            assignment_mode = 'admin_choice'

        # Create service request without any worker assignment
        service_request = ServiceRequest.objects.create(
            client=request.user,
            category=category,
            title=request.data.get('title', f"{category.name} Service Request"),
            description=request.data.get('description', ''),
            location=request.data.get('location', ''),
            city=request.data.get('city', ''),
            latitude=latitude,
            longitude=longitude,
            preferred_worker=preferred_worker,
            assignment_mode=assignment_mode,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            duration_type=duration_type,
            duration_days=duration_days,
            service_start_date=service_start_date,
            service_end_date=service_end_date,
            workers_needed=workers_needed,  # NEW: Store workers needed
            daily_rate=daily_rate,
            # snapshot the fee so a later category change cannot rewrite history
            service_fee=service_fee,
            total_price=total_price,
            urgency=request.data.get('urgency', 'normal'),
            client_notes=request.data.get('client_notes', ''),
            status='pending',  # Admin will review and assign worker(s)
            # Payment info. Deliberately created unpaid: the reference the
            # caller supplied is verified below before anything is marked paid.
            payment_status='pending',
            payment_method=request.data.get('payment_method', ''),
            payment_transaction_id='',
            paid_at=None,
        )

        # A booking used to be marked 'paid' purely because the caller sent a
        # payment_transaction_id - any string at all, so a client could declare
        # their own booking paid and receive the service for free. Only a
        # reference this server issued, to this client, for this amount, and
        # not already spent, is accepted.
        supplied_reference = (request.data.get('payment_transaction_id') or '').strip()
        if supplied_reference:
            txn = PaymentTransaction.redeem(
                supplied_reference, request.user, expected_amount=total_price
            )
            if txn is not None:
                txn.consumed_by = service_request
                txn.consumed_at = timezone.now()
                txn.save(update_fields=['consumed_by', 'consumed_at'])
                service_request.payment_status = 'paid'
                service_request.payment_transaction_id = txn.reference
                service_request.paid_at = timezone.now()
                service_request.save(update_fields=[
                    'payment_status', 'payment_transaction_id', 'paid_at', 'updated_at',
                ])
            else:
                logger.warning(
                    "Rejected unverifiable payment reference %r from user %s",
                    supplied_reference[:32], request.user.pk,
                )
        
        # Handle payment screenshot if provided
        if 'payment_screenshot' in request.FILES:
            screenshot = request.FILES['payment_screenshot']
            try:
                validate_image_file(screenshot)
            except ValidationError as e:
                service_request.delete()
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            service_request.payment_screenshot = screenshot
            service_request.save()

        # Apply the client's chosen assignment mode (no-op unless
        # auto_nearest; falls back to admin_choice if it can't auto-assign)
        apply_assignment_mode(service_request)
        service_request.refresh_from_db()

        auto_assigned = service_request.assignment_mode == 'auto_nearest' and service_request.status == 'assigned'
        details = f'Our admin will review your payment and assign {workers_needed} suitable worker(s). You will be notified once workers are assigned.' if workers_needed > 1 else 'Our admin will review your payment and assign the most suitable worker. You will be notified once a worker is assigned.'
        if auto_assigned:
            details = 'A worker has been automatically assigned based on proximity to your location!'

        return Response({
            'id': service_request.id,
            'message': f'Your {category.name} service request has been submitted successfully!',
            'details': details,
            'workers_needed': workers_needed,
            'available_workers': available_workers,
            'availability_status': availability_status,
            'availability_message': availability_message,
            'status': service_request.status,
            'assignment_mode': service_request.assignment_mode,
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

        # cancel() releases every active assignment and frees up each
        # worker's availability, and notifies them - a plain status flip
        # here used to leave assignments/worker availability untouched.
        service_request.cancel()

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

        # This used to just flip ServiceRequest.status - same class of bug
        # as cancellation: every active assignment was left untouched, so
        # the worker(s) stayed 'busy' forever, completed_jobs never
        # incremented, and no agent commission was credited. Route each
        # active assignment through mark_completed() for those side
        # effects, then set the parent status directly too, since the
        # client force-completing is an explicit override and shouldn't
        # depend on mark_completed()'s own "all assignments done" count
        # (which never fires if there happen to be zero real assignments).
        for assignment in service_request.assignments.filter(status__in=['accepted', 'in_progress']):
            assignment.mark_completed()
            assignment.calculate_payment()

        service_request.refresh_from_db()
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()

        # Notify every worker that the client marked their assignment
        # finished. The import here used to be `from jobs.notifications
        # import NotificationService` - that module doesn't exist, so this
        # always raised ModuleNotFoundError, silently swallowed below, so
        # no worker was ever notified.
        try:
            from worker_connect.notification_service import NotificationService
            for assignment in service_request.assignments.filter(status='completed'):
                NotificationService.create_notification(
                    recipient=assignment.worker.user,
                    title="✅ Service Marked as Finished",
                    message=f"Client has marked '{service_request.title}' as finished. Great work!",
                    notification_type='job_completed',
                    content_object=service_request,
                    extra_data={
                        'service_request_id': service_request.id,
                        'assignment_id': assignment.id,
                    }
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_service_request(request, request_id):
    """
    Client rates a completed service request. ServiceRequest.client_rating/
    client_review already existed on the model and in ServiceRequestSerializer,
    but had no endpoint to actually set them - the mobile app's rating screen
    called a URL that was never registered.
    """
    try:
        service_request = ServiceRequest.objects.get(id=request_id, client=request.user)

        if service_request.status != 'completed':
            return Response(
                {'error': 'Only completed service requests can be rated'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guard against re-rating: without this, calling the endpoint twice
        # (e.g. a network retry, or the user re-opening the rating screen)
        # rolled the rating into the worker's average_rating/total_reviews
        # a second time, permanently corrupting the aggregate.
        if service_request.client_rating is not None:
            return Response(
                {'error': 'You have already rated this service request'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rating = request.data.get('rating')
        review = request.data.get('review', '')

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return Response({'error': 'rating must be an integer 1-5'}, status=status.HTTP_400_BAD_REQUEST)

        if rating < 1 or rating > 5:
            return Response({'error': 'rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)

        service_request.client_rating = rating
        service_request.client_review = review
        service_request.save(update_fields=['client_rating', 'client_review'])

        # Roll the rating into the worker's aggregate stats. assigned_worker
        # is the LEGACY single-worker field and is never populated by the
        # real multi-worker assignment flow (_create_assignment()) - reading
        # it here always silently no-ops. The actual assigned worker(s) live
        # on the assignments relation; rate every worker who completed this
        # request (usually exactly one, but a multi-worker job should credit
        # all of them, not an arbitrary "first" one).
        completed_assignments = service_request.assignments.filter(status='completed').select_related('worker')
        for assignment in completed_assignments:
            worker = assignment.worker
            new_total = worker.total_reviews + 1
            worker.average_rating = round(
                ((worker.average_rating * worker.total_reviews) + rating) / new_total, 2
            )
            worker.total_reviews = new_total
            worker.save(update_fields=['average_rating', 'total_reviews'])

        return Response({
            'message': 'Rating submitted successfully',
            'service_request': {
                'id': service_request.id,
                'client_rating': service_request.client_rating,
                'client_review': service_request.client_review,
            }
        })
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error rating service request: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to submit rating'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_service_request(request, request_id):
    """Update a service request (including payment screenshot upload)"""
    try:
        service_request = ServiceRequest.objects.get(id=request_id, client=request.user)

        # Check if we're uploading a payment screenshot
        if 'payment_screenshot' in request.FILES:
            screenshot = request.FILES['payment_screenshot']
            try:
                validate_image_file(screenshot)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            service_request.payment_screenshot = screenshot
            service_request.save()

            return Response({
                'message': 'Payment screenshot uploaded successfully',
                'service_request': {
                    'id': service_request.id,
                    'has_screenshot': True,
                    'payment_verified': service_request.payment_verified
                }
            })
        
        # Otherwise, update other fields. 'workers_needed' is editable from
        # the mobile edit-service-request screen (see
        # app/(client)/edit-service-request/[id].tsx) but was missing here,
        # so that field was silently dropped on every save - the client
        # would change the worker count, get a "success" response, and the
        # value would just revert back on reload.
        allowed_fields = ['title', 'description', 'location', 'city', 'preferred_date',
                         'preferred_time', 'estimated_duration_hours', 'urgency', 'client_notes',
                         'workers_needed']

        for field in allowed_fields:
            if field in request.data:
                setattr(service_request, field, request.data[field])

        # workers_needed feeds directly into total_price
        # ((daily_rate x workers_needed) + service_fee) - recalculate so an
        # edited worker count doesn't leave the client with a stale price.
        if 'workers_needed' in request.data:
            service_request.calculate_total_price()

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
        from django.core.paginator import Paginator
        page_number = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        paginator = Paginator(favorites, page_size)
        page_obj = paginator.get_page(page_number)

        # Serialize favorites with worker details
        favorites_data = []
        for favorite in page_obj.object_list:
            worker = favorite.worker
            worker_data = {
                'id': favorite.id,
                'worker_id': worker.id,
                'worker_name': worker.user.get_full_name(),
                'worker_username': worker.user.username,
                'categories': [cat.name for cat in worker.categories.all()],
                'rating': worker.average_rating,
                'total_reviews': worker.total_reviews,
                'completed_jobs': worker.completed_jobs,
                'availability': worker.availability,
                'bio': worker.bio,
                'city': worker.city,
                'profile_picture': request.build_absolute_uri(worker.profile_image.url) if worker.profile_image else None,
                'added_at': favorite.created_at.isoformat(),
            }
            favorites_data.append(worker_data)
        
        return Response({
            'results': favorites_data,
            'count': paginator.count,
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
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
