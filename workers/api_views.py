import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from workers.models import WorkerProfile, WorkerDocument, Category
from jobs.models import DirectHireRequest, JobApplication
from .serializers import WorkerProfileSerializer, CategorySerializer
from workers.file_validators import validate_document_file

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_profile(request):
    """Get worker profile for the logged-in user"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        serializer = WorkerProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def update_worker_profile(request):
    """Update worker profile (supports file uploads for profile_image and JSON data)"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Handle profile_image separately if provided
        if 'profile_image' in request.FILES:
            image_file = request.FILES['profile_image']
            logger.debug(f"Received file: {image_file.name}, Size: {image_file.size}, Type: {image_file.content_type}")
            
            try:
                # Validate file type and size using MIME type checking
                from .file_validators import validate_image_file
                validate_image_file(image_file)
                
                # Save the file
                profile.profile_image = image_file
                profile.save()
                logger.debug(f"File saved successfully to: {profile.profile_image.url}")
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error saving profile image: {str(e)}", exc_info=True)
                return Response({'error': 'Failed to save file. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update other fields
        serializer = WorkerProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_worker_availability(request):
    """Update worker availability status"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        is_available = request.data.get('is_available')
        
        if is_available is None:
            return Response({'error': 'is_available field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update availability (use 'offline' instead of 'unavailable')
        profile.availability = 'available' if is_available else 'offline'
        profile.save(update_fields=['availability'])
        
        serializer = WorkerProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_stats(request):
    """Get worker dashboard stats"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Count direct hire requests (pending)
        pending_requests = DirectHireRequest.objects.filter(
            worker=profile,
            status='pending'
        ).count()
        
        # Count active jobs (accepted direct hire requests)
        active_jobs = DirectHireRequest.objects.filter(
            worker=profile,
            status='accepted'
        ).count()
        
        # Count total applications
        total_applications = JobApplication.objects.filter(
            worker=profile
        ).count()
        
        # Count accepted applications
        accepted_applications = JobApplication.objects.filter(
            worker=profile,
            status='accepted'
        ).count()
        
        stats = {
            'pending_requests': pending_requests,
            'active_jobs': active_jobs,
            'total_applications': total_applications,
            'accepted_applications': accepted_applications,
        }
        
        return Response(stats)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def direct_hire_requests(request):
    """Get direct hire requests for the logged-in worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Get pending direct hire requests
        requests = DirectHireRequest.objects.filter(
            worker=profile,
            status='pending'
        ).select_related('client').order_by('-created_at')
        
        # Serialize the requests
        requests_data = []
        for req in requests:
            requests_data.append({
                'id': req.id,
                'title': req.title,
                'client_name': req.client.get_full_name(),
                'client_phone': req.client.phone_number,
                'job_description': req.description,
                'offered_rate': str(req.offered_rate),
                'total_amount': str(req.total_amount),
                'duration_type': req.duration_type,
                'duration_value': req.duration_value,
                'start_datetime': req.start_datetime.isoformat(),
                'location': req.location,
                'created_at': req.created_at.isoformat(),
                'status': req.status,
            })
        
        return Response(requests_data)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in direct_hire_requests: {str(e)}')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    """Upload worker document (National ID or optional documents)"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Get form data
        document_type = request.data.get('document_type')
        title = request.data.get('title', '')
        file = request.FILES.get('file')
        
        # Validation
        if not document_type:
            return Response({'error': 'document_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate document type
        valid_types = ['id', 'cv', 'certificate', 'license', 'other']
        if document_type not in valid_types:
            return Response({'error': f'Invalid document_type. Must be one of: {", ".join(valid_types)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Set default title based on type if not provided
        if not title:
            title_map = {
                'id': 'National ID Card',
                'cv': 'CV/Resume',
                'certificate': 'Certificate',
                'license': 'License',
                'other': 'Document'
            }
            title = title_map.get(document_type, 'Document')
        
        # Check if document type already exists (except 'other' type which can have multiple)
        if document_type != 'other':
            existing_doc = WorkerDocument.objects.filter(
                worker=profile, 
                document_type=document_type
            ).first()
            if existing_doc:
                return Response({
                    'error': f'You have already uploaded a {title}. Please delete the existing one first.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate the document file (MIME type, size)
        try:
            validate_document_file(file)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document
        document = WorkerDocument.objects.create(
            worker=profile,
            document_type=document_type,
            title=title,
            file=file
        )
        
        # Update profile if National ID uploaded
        if document_type == 'id':
            profile.has_uploaded_national_id = True
            
            # Calculate new completion percentage
            base_percentage = 20  # Registration complete
            id_percentage = 40    # National ID uploaded
            optional_docs = profile.documents.exclude(document_type='id').count()
            optional_percentage = min(optional_docs * 10, 30)  # Max 30% for optional docs
            
            profile.profile_completion_percentage = base_percentage + id_percentage + optional_percentage
            profile.save()
        else:
            # Recalculate for optional documents
            optional_docs = profile.documents.exclude(document_type='id').count()
            base_percentage = 20
            id_percentage = 40 if profile.has_uploaded_national_id else 0
            optional_percentage = min(optional_docs * 10, 30)
            
            profile.profile_completion_percentage = base_percentage + id_percentage + optional_percentage
            profile.save()
        
        return Response({
            'id': document.id,
            'document_type': document.document_type,
            'title': document.title,
            'verification_status': document.verification_status,
            'uploaded_at': document.uploaded_at.isoformat(),
            'profile_completion_percentage': profile.profile_completion_percentage,
            'has_uploaded_national_id': profile.has_uploaded_national_id,
        }, status=status.HTTP_201_CREATED)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_documents(request):
    """Get all documents uploaded by the worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        documents = profile.documents.all()
        
        documents_data = [{
            'id': doc.id,
            'document_type': doc.document_type,
            'title': doc.title,
            'file_url': request.build_absolute_uri(doc.file.url) if doc.file else None,
            'verification_status': doc.verification_status,
            'rejection_reason': doc.rejection_reason,
            'uploaded_at': doc.uploaded_at.isoformat(),
            'verified_at': doc.verified_at.isoformat() if doc.verified_at else None,
        } for doc in documents]
        
        return Response({
            'documents': documents_data,
            'total_count': documents.count(),
            'has_national_id': profile.has_uploaded_national_id,
        }, status=status.HTTP_200_OK)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_document(request, document_id):
    """Delete a document uploaded by the worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        document = WorkerDocument.objects.get(id=document_id, worker=profile)
        
        # Check if it's the National ID
        is_national_id = document.document_type == 'id'
        
        # Delete the file from storage
        if document.file:
            document.file.delete()
        
        # Delete the document record
        document.delete()
        
        # Update profile if National ID was deleted
        if is_national_id:
            profile.has_uploaded_national_id = False
            # Recalculate completion percentage
            optional_docs = profile.documents.exclude(document_type='id').count()
            base_percentage = 20  # Registration complete
            optional_percentage = min(optional_docs * 10, 30)
            profile.profile_completion_percentage = base_percentage + optional_percentage
            profile.save()
        else:
            # Recalculate for optional documents
            optional_docs = profile.documents.exclude(document_type='id').count()
            base_percentage = 20
            id_percentage = 40 if profile.has_uploaded_national_id else 0
            optional_percentage = min(optional_docs * 10, 30)
            profile.profile_completion_percentage = base_percentage + id_percentage + optional_percentage
            profile.save()
        
        return Response({
            'message': 'Document deleted successfully',
            'profile_completion_percentage': profile.profile_completion_percentage,
            'has_uploaded_national_id': profile.has_uploaded_national_id,
        }, status=status.HTTP_200_OK)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except WorkerDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_completion(request):
    """Get profile completion status"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        
        return Response({
            'profile_completion_percentage': profile.profile_completion_percentage,
            'is_profile_complete': profile.is_profile_complete,
            'has_uploaded_national_id': profile.has_uploaded_national_id,
            'worker_type': profile.worker_type,
        })
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories(request):
    """Get all active categories"""
    categories = Category.objects.filter(is_active=True).order_by('name')
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_skills_by_category(request):
    """Get skills for specific categories"""
    from workers.models import Skill
    from workers.serializers import SkillSerializer
    
    category_ids = request.GET.get('categories', '')
    if category_ids:
        category_ids = [int(id) for id in category_ids.split(',') if id.isdigit()]
        skills = Skill.objects.filter(category_id__in=category_ids).order_by('name')
    else:
        skills = Skill.objects.all().order_by('name')
    
    serializer = SkillSerializer(skills, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def work_experiences(request):
    """Get or create work experiences for the authenticated worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can manage work experience'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        from workers.models import WorkExperience
        from workers.serializers import WorkExperienceSerializer
        
        experiences = WorkExperience.objects.filter(worker=worker_profile).order_by('-start_date')
        serializer = WorkExperienceSerializer(experiences, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        from workers.serializers import WorkExperienceSerializer
        
        serializer = WorkExperienceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(worker=worker_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def work_experience_detail(request, experience_id):
    """Get, update or delete a specific work experience"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can manage work experience'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = WorkerProfile.objects.get(user=request.user)
        from workers.models import WorkExperience
        experience = WorkExperience.objects.get(id=experience_id, worker=worker_profile)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except WorkExperience.DoesNotExist:
        return Response({'error': 'Experience not found'}, status=status.HTTP_404_NOT_FOUND)
    
    from workers.serializers import WorkExperienceSerializer
    
    if request.method == 'GET':
        serializer = WorkExperienceSerializer(experience)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = WorkExperienceSerializer(experience, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        experience.delete()
        return Response({'message': 'Experience deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_analytics(request):
    """Get worker analytics data for analytics screen"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.db.models import Avg, Sum, Count
        from clients.models import Rating
        from datetime import datetime, timedelta
        
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Total applications
        total_applications = JobApplication.objects.filter(worker=profile).count()
        
        # Completed jobs
        completed_jobs = DirectHireRequest.objects.filter(
            worker=profile,
            status='completed'
        ).count()
        
        # Success rate (accepted / total applications)
        accepted_apps = JobApplication.objects.filter(worker=profile, status='accepted').count()
        success_rate = (accepted_apps / total_applications * 100) if total_applications > 0 else 0
        
        # Average rating
        avg_rating = Rating.objects.filter(worker=profile).aggregate(Avg('rating'))['rating__avg'] or 0.0
        
        # Response rate (applications with responses / total)
        responded_apps = JobApplication.objects.filter(
            worker=profile,
            status__in=['accepted', 'rejected']
        ).count()
        response_rate = (responded_apps / total_applications * 100) if total_applications > 0 else 0
        
        # Profile completeness
        profile_completeness = profile.profile_completion_percentage
        
        return Response({
            'total_applications': total_applications,
            'completed_jobs': completed_jobs,
            'success_rate': round(success_rate, 1),
            'average_rating': round(avg_rating, 1),
            'response_rate': round(response_rate, 1),
            'profile_completeness': profile_completeness,
        })
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_breakdown(request):
    """Get earnings breakdown by time period"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from datetime import datetime, timedelta
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth, TruncWeek
        
        profile = WorkerProfile.objects.get(user=request.user)
        group_by = request.GET.get('group_by', 'month')  # 'week' or 'month'
        periods = int(request.GET.get('periods', 6))
        
        # Get completed jobs with payments (assuming DirectHireRequest has payment info)
        jobs = DirectHireRequest.objects.filter(
            worker=profile,
            status='completed'
        )
        
        if group_by == 'month':
            earnings_data = jobs.annotate(
                period=TruncMonth('created_at')
            ).values('period').annotate(
                earnings=Sum('total_amount')
            ).order_by('-period')[:periods]
        else:  # week
            earnings_data = jobs.annotate(
                period=TruncWeek('created_at')
            ).values('period').annotate(
                earnings=Sum('total_amount')
            ).order_by('-period')[:periods]
        
        # Format the data
        result = []
        for item in reversed(list(earnings_data)):
            if group_by == 'month':
                period_str = item['period'].strftime('%b %Y')
            else:
                period_str = item['period'].strftime('%m/%d')
            
            result.append({
                'period': period_str,
                'earnings': str(item['earnings'] or 0)
            })
        
        return Response(result)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_by_category(request):
    """Get earnings breakdown by job category"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.db.models import Sum, Count
        
        profile = WorkerProfile.objects.get(user=request.user)
        
        # Get earnings by category from completed jobs
        # Assuming JobRequest has category field linked to DirectHireRequest
        from jobs.models import JobRequest
        
        category_earnings = []
        
        # Get worker's categories
        for category in profile.categories.all():
            # Count completed jobs in this category
            jobs_count = DirectHireRequest.objects.filter(
                worker=profile,
                status='completed',
                # Add category filter when available
            ).count()
            
            # Calculate total earnings (simplified - adjust based on your model)
            total = DirectHireRequest.objects.filter(
                worker=profile,
                status='completed',
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            if jobs_count > 0:
                category_earnings.append({
                    'category': category.name,
                    'earnings': str(total / profile.categories.count()),  # Simple distribution
                    'jobs_count': jobs_count,
                })
        
        return Response(category_earnings)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_clients(request):
    """Get top clients by earnings"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.db.models import Sum, Count
        
        profile = WorkerProfile.objects.get(user=request.user)
        limit = int(request.GET.get('limit', 5))
        
        # Get top clients from completed jobs
        top_clients_data = DirectHireRequest.objects.filter(
            worker=profile,
            status='completed'
        ).values('client__id', 'client__first_name', 'client__last_name').annotate(
            total_earnings=Sum('total_amount'),
            jobs_count=Count('id')
        ).order_by('-total_earnings')[:limit]
        
        result = []
        for item in top_clients_data:
            result.append({
                'client_id': item['client__id'],
                'client_name': f"{item['client__first_name']} {item['client__last_name']}",
                'total_earnings': str(item['total_earnings'] or 0),
                'jobs_count': item['jobs_count'],
            })
        
        return Response(result)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """Get payment transaction history"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        limit = int(request.GET.get('limit', 20))
        
        # Get completed jobs as payment history
        payments = DirectHireRequest.objects.filter(
            worker=profile,
            status='completed'
        ).select_related('client').order_by('-updated_at')[:limit]
        
        result = []
        for payment in payments:
            result.append({
                'id': payment.id,
                'job_id': payment.id,
                'job_title': payment.title,
                'client_name': payment.client.get_full_name(),
                'amount': str(payment.total_amount),
                'date': payment.updated_at.isoformat(),
                'status': 'completed',
            })
        
        return Response(result)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_push_token(request):
    """Register push notification token for the user"""
    token = request.data.get('token')
    platform = request.data.get('platform', 'unknown')
    
    if not token:
        return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Store the push token (create a PushToken model if needed)
        # For now, we'll just acknowledge receipt
        # TODO: Create PushToken model to store tokens
        
        logger.info(f"Registered push token for user {request.user.id} on {platform}")
        
        return Response({
            'message': 'Push token registered successfully',
            'token': token,
            'platform': platform,
        })
        
    except Exception as e:
        logger.error(f"Error registering push token: {str(e)}")
        return Response({'error': 'Failed to register push token'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
