import logging
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Avg
from workers.models import WorkerProfile, WorkerDocument, Category
from jobs.models import DirectHireRequest, JobApplication
from .serializers import WorkerProfileSerializer, CategorySerializer
from workers.file_validators import validate_document_file

logger = logging.getLogger(__name__)


class QueryParamTokenAuthentication(TokenAuthentication):
    """
    Same as TokenAuthentication, but also accepts the token via a `?token=`
    query parameter. Used only for the CV PDF download link, which the
    mobile app opens in an external browser tab (no Authorization header).
    """

    def authenticate(self, request):
        auth = super().authenticate(request)
        if auth is not None:
            return auth

        token = request.query_params.get('token')
        if not token:
            return None
        return self.authenticate_credentials(token)


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
@permission_classes([AllowAny])
def featured_workers(request):
    """Get featured workers for client dashboard"""
    try:
        # Get top-rated available workers. average_rating/completed_jobs
        # are already real, maintained fields on WorkerProfile - no need
        # to (mis)annotate them from unrelated relations.
        featured = WorkerProfile.objects.filter(
            availability='available',
            is_profile_complete=True,
            is_public=True,
            average_rating__gte=4.0,  # Only workers with 4+ rating
        ).order_by('-average_rating', '-completed_jobs')[:6]
        
        # Serialize data
        workers_data = []
        for worker in featured:
            workers_data.append({
                'id': worker.id,
                'name': worker.user.get_full_name(),
                'categories': [{'name': cat.name} for cat in worker.categories.all()],
                'average_rating': float(worker.average_rating or 0),
                'completed_jobs': worker.completed_jobs,
                'availability': worker.availability,
                'profile_image': request.build_absolute_uri(worker.profile_image.url) if worker.profile_image else None,
            })
        
        return Response(workers_data)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in featured_workers: {str(e)}')
        return Response([], status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_stats(request):
    """Get worker dashboard stats"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from jobs.service_request_models import ServiceRequestAssignment
        worker_profile = WorkerProfile.objects.get(user=request.user)

        # This used to filter ServiceRequest.assigned_worker - the legacy
        # single-worker FK the real multi-worker assignment flow
        # (_create_assignment) never populates, so every count/sum here
        # was always zero for every worker. Use the real per-worker
        # ServiceRequestAssignment relation instead (matching the pattern
        # already established in worker_analytics() below).
        my_assignments = ServiceRequestAssignment.objects.filter(worker=worker_profile)

        assigned_jobs_total = my_assignments.count()
        active_jobs = my_assignments.filter(status='in_progress').count()
        completed_jobs = my_assignments.filter(status='completed').count()
        pending_jobs = my_assignments.filter(status='pending').count()

        # Accepted (not yet finished) - used for response_rate below
        accepted_jobs = my_assignments.filter(
            status__in=['accepted', 'in_progress', 'completed']
        ).count()

        from django.db.models import Sum
        # Earnings from completed assignments - worker_payment is this
        # worker's own cut, not the request's total_price (which covers
        # every worker on a multi-worker request)
        total_earnings = my_assignments.filter(
            status='completed'
        ).aggregate(total=Sum('worker_payment'))['total'] or 0

        # Pending earnings from active jobs (earned but pending payment)
        pending_earnings = my_assignments.filter(
            status='in_progress'
        ).aggregate(total=Sum('worker_payment'))['total'] or 0

        # response_rate is the one field the mobile app's profile screen
        # actually reads from this endpoint (statsData.response_rate) -
        # it was missing from the response entirely, so it always showed
        # 0% regardless of the worker's real accept rate.
        response_rate = (accepted_jobs / assigned_jobs_total * 100) if assigned_jobs_total > 0 else 0

        stats = {
            'assigned_jobs': assigned_jobs_total,
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
            'pending_jobs': pending_jobs,
            'total_earnings': float(total_earnings),
            'pending_earnings': float(pending_earnings),
            'withdrawn_earnings': 0,
            'response_rate': round(response_rate, 1),
        }

        return Response(stats)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assigned_jobs(request):
    """Get jobs assigned to this worker"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from jobs.service_request_models import ServiceRequest
        profile = WorkerProfile.objects.get(user=request.user)

        # Get service requests assigned to this worker - via the real
        # assignments relation, not the legacy assigned_worker FK that the
        # live multi-worker assignment flow never populates (this always
        # returned an empty list before).
        jobs = ServiceRequest.objects.filter(
            assignments__worker=profile
        ).distinct().select_related('client', 'category').order_by('-created_at')
        
        # Serialize the jobs
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'status': job.status,
                'urgency': job.urgency,
                'location': job.location,
                'city': job.city,
                'total_price': float(job.total_price) if job.total_price else None,
                'duration_days': job.duration_days,
                'created_at': job.created_at.isoformat(),
                'client': {
                    'id': job.client.id,
                    'name': job.client.get_full_name(),
                    'email': job.client.email,
                    'phone': job.client.phone_number,
                },
                'category': {
                    'id': job.category.id if job.category else None,
                    'name': job.category.name if job.category else None,
                } if job.category else None,
            })
        
        return Response({'jobs': jobs_data})
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_job_status(request, job_id):
    """Update status of assigned job"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
        profile = WorkerProfile.objects.get(user=request.user)

        # Get the service request and verify worker is assigned - via the
        # real assignments relation. assigned_worker_id is the legacy
        # single-worker FK the live multi-worker assignment flow never
        # populates, so this always 403'd for every worker before.
        job = ServiceRequest.objects.get(id=job_id)
        assignment = ServiceRequestAssignment.objects.filter(
            service_request=job, worker=profile
        ).exclude(status__in=['rejected', 'cancelled']).first()
        if not assignment:
            return Response({'error': 'You are not assigned to this job'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        valid_statuses = ['in_progress', 'completed']

        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == 'completed':
            # mark_completed() is what actually frees the worker back to
            # 'available', increments completed_jobs, and credits any
            # recruiting agent's commission - setting job.status directly
            # skipped all of that.
            assignment.mark_completed()
            assignment.calculate_payment()
        else:
            assignment.status = new_status
            assignment.save(update_fields=['status', 'updated_at'])
            job.status = new_status
            job.save(update_fields=['status'])

        # Send notification to client
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(
            recipient=job.client,
            title='Job Status Updated',
            message=f'Your job "{job.title}" is now {new_status.replace("_", " ").title()}',
            notification_type='job_completed' if new_status == 'completed' else 'system_alert',
            content_object=job,
            extra_data={'service_request_id': job.id, 'assignment_id': assignment.id}
        )

        return Response({'message': 'Job status updated successfully', 'status': new_status})
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


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
            # A worker with no ID document on file can no longer be considered
            # verified - without this, deleting an approved ID leaves
            # verification_status='verified' (and the "Verified Worker" badge)
            # in place with nothing backing it.
            if profile.verification_status == 'verified':
                profile.verification_status = 'pending'
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
def worker_cv(request):
    """Get the auto-generated CV data for the authenticated worker (mobile app)"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)

    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)

    from .cv import CVService
    context = CVService.get_cv_context(profile)

    return Response({
        'full_name': context['full_name'],
        'email': context['email'],
        'phone_number': context['phone_number'],
        'location': context['location'],
        'bio': context['bio'],
        'worker_type': context['worker_type'],
        'experience_years': context['experience_years'],
        'average_rating': str(context['average_rating']),
        'completed_jobs': context['completed_jobs'],
        'verification_status': context['verification_status'],
        'profile_image_url': request.build_absolute_uri(context['profile_image_url']) if context['profile_image_url'] else None,
        'is_complete': context['is_complete'],
        'categories': [{'id': c.id, 'name': c.name} for c in context['categories']],
        'skills': [{'id': s.id, 'name': s.name} for s in context['skills']],
        'experiences': [
            {
                'id': exp.id,
                'job_title': exp.job_title,
                'company': exp.company,
                'location': exp.location,
                'start_date': exp.start_date.isoformat() if exp.start_date else None,
                'end_date': exp.end_date.isoformat() if exp.end_date else None,
                'is_current': exp.is_current,
                'description': exp.description,
                'duration': exp.duration,
            }
            for exp in context['experiences']
        ],
    })


@api_view(['GET'])
@authentication_classes([QueryParamTokenAuthentication])
@permission_classes([IsAuthenticated])
def worker_cv_download(request):
    """Download the authenticated worker's auto-generated CV as a PDF (mobile app)"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)

    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)

    from django.http import HttpResponse
    from .cv import CVService

    pdf = CVService.generate_pdf(profile)
    if not pdf:
        return Response({'error': 'PDF generation not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{profile.user.username}_CV.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_analytics(request):
    """Get worker analytics data for analytics screen"""
    if request.user.user_type != 'worker':
        return Response({'error': 'Only workers can access this'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from jobs.service_request_models import ServiceRequestAssignment

        profile = WorkerProfile.objects.get(user=request.user)

        # Use ServiceRequestAssignment - the real per-worker assignment
        # relation that supports multiple workers on one ServiceRequest.
        # The legacy ServiceRequest.assigned_worker field only ever points
        # at one worker, so a second/third worker assigned to the same
        # request would show zero analytics if we filtered on that instead.
        my_assignments = ServiceRequestAssignment.objects.filter(worker=profile)

        # Total assignments (ever assigned to this worker)
        total_assignments = my_assignments.count()

        # Completed assignments
        completed_jobs = my_assignments.filter(status='completed').count()

        # Accepted assignments (not pending/rejected/cancelled)
        accepted_assignments = my_assignments.filter(
            status__in=['accepted', 'in_progress', 'completed']
        ).count()

        # Success rate (completed / total)
        success_rate = (completed_jobs / total_assignments * 100) if total_assignments > 0 else 0

        # Response rate (accepted / total)
        response_rate = (accepted_assignments / total_assignments * 100) if total_assignments > 0 else 0

        # Average rating - use the maintained WorkerProfile field rather than
        # recomputing from ServiceRequest.client_rating, which rates the
        # overall (possibly multi-worker) service request, not this worker.
        avg_rating = float(profile.average_rating or 0)

        # Profile completeness
        profile_completeness = profile.profile_completion_percentage
        
        return Response({
            'total_applications': total_assignments,
            'accepted_applications': accepted_assignments,
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
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth, TruncWeek
        from jobs.service_request_models import ServiceRequestAssignment

        profile = WorkerProfile.objects.get(user=request.user)
        group_by = request.GET.get('group_by', 'month')  # 'week' or 'month'
        periods = int(request.GET.get('periods', 6))

        # Get this worker's completed assignments (the real, current
        # multi-worker relation - not the legacy ServiceRequest.assigned_worker).
        # Exclude rows with no work_completed_at: TruncMonth/TruncWeek group
        # them under a None period, and formatting that period below would
        # crash with AttributeError: 'NoneType' object has no attribute
        # 'strftime' instead of just omitting them from the breakdown.
        jobs = ServiceRequestAssignment.objects.filter(
            worker=profile,
            status='completed',
            work_completed_at__isnull=False,
        )

        if group_by == 'month':
            earnings_data = jobs.annotate(
                period=TruncMonth('work_completed_at')
            ).values('period').annotate(
                earnings=Sum('worker_payment')
            ).order_by('-period')[:periods]
        else:  # week
            earnings_data = jobs.annotate(
                period=TruncWeek('work_completed_at')
            ).values('period').annotate(
                earnings=Sum('worker_payment')
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
        from jobs.service_request_models import ServiceRequestAssignment

        profile = WorkerProfile.objects.get(user=request.user)

        # Group this worker's completed assignments by category (real,
        # current multi-worker relation - not the legacy assigned_worker FK)
        category_data = ServiceRequestAssignment.objects.filter(
            worker=profile,
            status='completed'
        ).values('service_request__category__name').annotate(
            jobs_count=Count('id'),
            earnings=Sum('worker_payment')
        ).order_by('-earnings')
        
        result = []
        for item in category_data:
            result.append({
                'category': item['service_request__category__name'] or 'Uncategorised',
                'earnings': str(item['earnings'] or 0),
                'jobs_count': item['jobs_count'],
            })
        
        return Response(result)
        
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
        from jobs.service_request_models import ServiceRequestAssignment

        profile = WorkerProfile.objects.get(user=request.user)
        limit = int(request.GET.get('limit', 5))

        # Get top clients from this worker's completed assignments (real,
        # current multi-worker relation - not the legacy assigned_worker FK)
        top_clients_data = ServiceRequestAssignment.objects.filter(
            worker=profile,
            status='completed'
        ).values(
            'service_request__client__id',
            'service_request__client__first_name',
            'service_request__client__last_name',
        ).annotate(
            total_earnings=Sum('worker_payment'),
            jobs_count=Count('id')
        ).order_by('-total_earnings')[:limit]
        
        result = []
        for item in top_clients_data:
            result.append({
                'client_id': item['service_request__client__id'],
                'client_name': f"{item['service_request__client__first_name']} {item['service_request__client__last_name']}",
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
        from jobs.service_request_models import ServiceRequestAssignment
        profile = WorkerProfile.objects.get(user=request.user)
        limit = int(request.GET.get('limit', 20))

        # Get this worker's completed assignments as payment history (real,
        # current multi-worker relation - not the legacy assigned_worker FK)
        payments = ServiceRequestAssignment.objects.filter(
            worker=profile,
            status='completed'
        ).select_related('service_request__client').order_by('-work_completed_at')[:limit]

        result = []
        for assignment in payments:
            service_request = assignment.service_request
            result.append({
                'id': assignment.id,
                'job_id': service_request.id,
                'job_title': service_request.title,
                'client_name': service_request.client.get_full_name(),
                'amount': str(assignment.worker_payment or 0),
                'date': (assignment.work_completed_at or assignment.assigned_at).isoformat(),
                'status': 'completed',
            })
        
        return Response(result)
        
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)


# NOTE: push token registration lives in worker_connect/notification_views.py
# (backed by the PushToken model). This module used to have its own
# register_push_token that accepted tokens but never persisted them, and
# nothing in the mobile app called it - removed rather than duplicated.
