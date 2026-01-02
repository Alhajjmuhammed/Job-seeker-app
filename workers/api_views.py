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
