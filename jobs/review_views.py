"""
Review API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from accounts.models import User
from jobs.models import JobRequest
from .reviews import Review, ReviewService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request):
    """
    Create a review for a user.
    
    Request body:
        {
            "reviewee_id": 1,
            "job_id": 1,  // optional
            "overall_rating": 5,
            "communication_rating": 5,  // optional
            "quality_rating": 5,  // optional
            "punctuality_rating": 5,  // optional
            "professionalism_rating": 5,  // optional
            "title": "Great work!",  // optional
            "comment": "Detailed review...",
            "would_recommend": true,  // optional
            "would_hire_again": true  // optional
        }
    """
    reviewee_id = request.data.get('reviewee_id')
    job_id = request.data.get('job_id')
    overall_rating = request.data.get('overall_rating')
    
    if not reviewee_id:
        return Response({
            'error': 'reviewee_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not overall_rating or overall_rating < 1 or overall_rating > 5:
        return Response({
            'error': 'overall_rating (1-5) is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    reviewee = get_object_or_404(User, id=reviewee_id)
    
    if reviewee == request.user:
        return Response({
            'error': 'You cannot review yourself'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    job = None
    if job_id:
        job = get_object_or_404(JobRequest, id=job_id)
    
    result = ReviewService.create_review(
        reviewer=request.user,
        reviewee=reviewee,
        job=job,
        overall_rating=overall_rating,
        comment=request.data.get('comment', ''),
        title=request.data.get('title', ''),
        communication_rating=request.data.get('communication_rating'),
        quality_rating=request.data.get('quality_rating'),
        punctuality_rating=request.data.get('punctuality_rating'),
        professionalism_rating=request.data.get('professionalism_rating'),
        would_recommend=request.data.get('would_recommend'),
        would_hire_again=request.data.get('would_hire_again'),
    )
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_user_reviews(request, user_id):
    """
    Get reviews for a user.
    
    Query params:
        - type: 'client_to_worker' or 'worker_to_client' (optional)
        - limit: Max results (default: 20)
        - offset: Pagination offset (default: 0)
    """
    user = get_object_or_404(User, id=user_id)
    
    review_type = request.query_params.get('type')
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    result = ReviewService.get_reviews_for_user(
        user,
        review_type=review_type,
        limit=limit,
        offset=offset
    )
    
    return Response({
        'user_id': user_id,
        'user_name': user.get_full_name() or user.username,
        **result
    })


@api_view(['GET'])
def get_rating_summary(request, user_id):
    """
    Get rating summary for a user.
    """
    user = get_object_or_404(User, id=user_id)
    
    summary = ReviewService.get_rating_summary(user)
    
    return Response({
        'user_id': user_id,
        'user_name': user.get_full_name() or user.username,
        **summary
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_reviews(request):
    """
    Get reviews for the authenticated user.
    """
    result = ReviewService.get_reviews_for_user(request.user)
    summary = ReviewService.get_rating_summary(request.user)
    
    return Response({
        'summary': summary,
        **result
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reviews_given(request):
    """
    Get reviews given by the authenticated user.
    """
    reviews = Review.objects.filter(
        reviewer=request.user
    ).select_related('reviewee', 'job').order_by('-created_at')
    
    reviews_data = []
    for review in reviews[:50]:
        reviews_data.append({
            'id': review.id,
            'reviewee': {
                'id': review.reviewee.id,
                'name': review.reviewee.get_full_name() or review.reviewee.username,
            },
            'job': {
                'id': review.job.id,
                'title': review.job.title,
            } if review.job else None,
            'overall_rating': review.overall_rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat(),
        })
    
    return Response({
        'count': len(reviews_data),
        'reviews': reviews_data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_review(request, review_id):
    """
    Add a response to a review.
    
    Request body:
        {
            "response": "Thank you for your feedback..."
        }
    """
    response_text = request.data.get('response', '')
    
    if not response_text:
        return Response({
            'error': 'response is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = ReviewService.respond_to_review(review_id, request.user, response_text)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def flag_review(request, review_id):
    """
    Flag a review for moderation.
    
    Request body:
        {
            "reason": "Inappropriate content"
        }
    """
    reason = request.data.get('reason', '')
    
    if not reason:
        return Response({
            'error': 'reason is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = ReviewService.flag_review(review_id, request.user, reason)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['GET'])
def get_job_reviews(request, job_id):
    """
    Get all reviews associated with a job.
    """
    job = get_object_or_404(JobRequest, id=job_id)
    
    reviews = Review.objects.filter(
        job=job,
        is_visible=True
    ).select_related('reviewer', 'reviewee')
    
    reviews_data = []
    for review in reviews:
        reviews_data.append({
            'id': review.id,
            'reviewer': {
                'id': review.reviewer.id,
                'name': review.reviewer.get_full_name() or review.reviewer.username,
            },
            'reviewee': {
                'id': review.reviewee.id,
                'name': review.reviewee.get_full_name() or review.reviewee.username,
            },
            'review_type': review.review_type,
            'overall_rating': review.overall_rating,
            'comment': review.comment,
            'response': review.response,
            'created_at': review.created_at.isoformat(),
        })
    
    return Response({
        'job_id': job_id,
        'job_title': job.title,
        'reviews': reviews_data,
    })
