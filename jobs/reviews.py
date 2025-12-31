"""
Review and rating system for Worker Connect.

Allows clients to review workers and workers to review clients.
"""

from django.db import models
from django.db.models import Avg, Count
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from typing import Dict, Any, List, Optional


class Review(models.Model):
    """
    Review/rating model for both workers and clients.
    """
    
    REVIEW_TYPE_CHOICES = [
        ('client_to_worker', 'Client reviewing Worker'),
        ('worker_to_client', 'Worker reviewing Client'),
    ]
    
    reviewer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews_given'
    )
    reviewee = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews_received'
    )
    job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews'
    )
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES)
    
    # Rating breakdown
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    quality_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text="Quality of work (for workers) or job description accuracy (for clients)"
    )
    punctuality_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    professionalism_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    
    # Review content
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)
    
    # Response from reviewee
    response = models.TextField(blank=True)
    response_at = models.DateTimeField(null=True, blank=True)
    
    # Moderation
    is_verified = models.BooleanField(default=True)  # Verified = from completed job
    is_visible = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    # Would recommend
    would_recommend = models.BooleanField(null=True, blank=True)
    would_hire_again = models.BooleanField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['reviewer', 'reviewee', 'job']
        indexes = [
            models.Index(fields=['reviewee', '-created_at']),
            models.Index(fields=['review_type', 'is_visible']),
            models.Index(fields=['job']),
        ]
    
    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username} ({self.overall_rating}★)"
    
    @property
    def average_rating(self):
        """Calculate average of all rating dimensions."""
        ratings = [
            self.overall_rating,
            self.communication_rating,
            self.quality_rating,
            self.punctuality_rating,
            self.professionalism_rating
        ]
        valid_ratings = [r for r in ratings if r is not None]
        return sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0


class ReviewService:
    """
    Service for managing reviews.
    """
    
    @staticmethod
    def create_review(
        reviewer,
        reviewee,
        job,
        overall_rating: int,
        comment: str = '',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new review.
        """
        from jobs.models import JobApplication
        
        # Determine review type
        if hasattr(reviewer, 'client_profile'):
            review_type = 'client_to_worker'
        else:
            review_type = 'worker_to_client'
        
        # Check if review already exists
        existing = Review.objects.filter(
            reviewer=reviewer,
            reviewee=reviewee,
            job=job
        ).first()
        
        if existing:
            return {
                'success': False,
                'error': 'You have already reviewed this user for this job'
            }
        
        # Verify job was completed and user was involved
        is_verified = False
        if job and job.status == 'completed':
            is_verified = True
        
        # Create review
        review = Review.objects.create(
            reviewer=reviewer,
            reviewee=reviewee,
            job=job,
            review_type=review_type,
            overall_rating=overall_rating,
            comment=comment,
            is_verified=is_verified,
            communication_rating=kwargs.get('communication_rating'),
            quality_rating=kwargs.get('quality_rating'),
            punctuality_rating=kwargs.get('punctuality_rating'),
            professionalism_rating=kwargs.get('professionalism_rating'),
            title=kwargs.get('title', ''),
            would_recommend=kwargs.get('would_recommend'),
            would_hire_again=kwargs.get('would_hire_again'),
        )
        
        # Update reviewee's average rating
        ReviewService._update_user_rating(reviewee)
        
        return {
            'success': True,
            'review_id': review.id,
            'message': 'Review submitted successfully'
        }
    
    @staticmethod
    def _update_user_rating(user):
        """Update user's aggregate rating."""
        from workers.models import WorkerProfile
        from clients.models import ClientProfile
        
        reviews = Review.objects.filter(
            reviewee=user,
            is_visible=True
        )
        
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=Avg('overall_rating'))['avg']
            count = reviews.count()
            
            # Update worker profile if exists
            if hasattr(user, 'worker_profile'):
                profile = user.worker_profile
                profile.average_rating = round(avg_rating, 2)
                profile.total_reviews = count
                profile.save()
            
            # Update client profile if exists
            if hasattr(user, 'client_profile'):
                profile = user.client_profile
                if hasattr(profile, 'average_rating'):
                    profile.average_rating = round(avg_rating, 2)
                    profile.total_reviews = count
                    profile.save()
    
    @staticmethod
    def get_reviews_for_user(
        user,
        review_type: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get reviews for a user.
        """
        queryset = Review.objects.filter(
            reviewee=user,
            is_visible=True
        ).select_related('reviewer', 'job')
        
        if review_type:
            queryset = queryset.filter(review_type=review_type)
        
        total = queryset.count()
        reviews = queryset[offset:offset + limit]
        
        reviews_data = []
        for review in reviews:
            reviews_data.append({
                'id': review.id,
                'reviewer': {
                    'id': review.reviewer.id,
                    'name': review.reviewer.get_full_name() or review.reviewer.username,
                },
                'job': {
                    'id': review.job.id,
                    'title': review.job.title,
                } if review.job else None,
                'overall_rating': review.overall_rating,
                'communication_rating': review.communication_rating,
                'quality_rating': review.quality_rating,
                'punctuality_rating': review.punctuality_rating,
                'professionalism_rating': review.professionalism_rating,
                'title': review.title,
                'comment': review.comment,
                'response': review.response,
                'is_verified': review.is_verified,
                'would_recommend': review.would_recommend,
                'created_at': review.created_at.isoformat(),
            })
        
        return {
            'total': total,
            'reviews': reviews_data,
        }
    
    @staticmethod
    def get_rating_summary(user) -> Dict[str, Any]:
        """
        Get rating summary for a user.
        """
        reviews = Review.objects.filter(
            reviewee=user,
            is_visible=True
        )
        
        if not reviews.exists():
            return {
                'total_reviews': 0,
                'average_rating': None,
                'rating_breakdown': {},
                'category_averages': {},
            }
        
        # Aggregate ratings
        aggregates = reviews.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_communication=Avg('communication_rating'),
            avg_quality=Avg('quality_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_professionalism=Avg('professionalism_rating'),
            total=Count('id'),
        )
        
        # Rating breakdown (count per star)
        breakdown = {}
        for i in range(1, 6):
            breakdown[str(i)] = reviews.filter(overall_rating=i).count()
        
        # Recommendation stats
        recommend_count = reviews.filter(would_recommend=True).count()
        hire_again_count = reviews.filter(would_hire_again=True).count()
        
        return {
            'total_reviews': aggregates['total'],
            'average_rating': round(aggregates['avg_overall'], 2) if aggregates['avg_overall'] else None,
            'rating_breakdown': breakdown,
            'category_averages': {
                'communication': round(aggregates['avg_communication'], 2) if aggregates['avg_communication'] else None,
                'quality': round(aggregates['avg_quality'], 2) if aggregates['avg_quality'] else None,
                'punctuality': round(aggregates['avg_punctuality'], 2) if aggregates['avg_punctuality'] else None,
                'professionalism': round(aggregates['avg_professionalism'], 2) if aggregates['avg_professionalism'] else None,
            },
            'would_recommend_percent': round(recommend_count / aggregates['total'] * 100, 1) if aggregates['total'] > 0 else None,
            'would_hire_again_percent': round(hire_again_count / aggregates['total'] * 100, 1) if aggregates['total'] > 0 else None,
        }
    
    @staticmethod
    def respond_to_review(review_id: int, user, response: str) -> Dict[str, Any]:
        """
        Add a response to a review.
        """
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return {'success': False, 'error': 'Review not found'}
        
        if review.reviewee != user:
            return {'success': False, 'error': 'You can only respond to reviews about you'}
        
        if review.response:
            return {'success': False, 'error': 'You have already responded to this review'}
        
        review.response = response
        review.response_at = timezone.now()
        review.save()
        
        return {
            'success': True,
            'message': 'Response added successfully'
        }
    
    @staticmethod
    def flag_review(review_id: int, user, reason: str) -> Dict[str, Any]:
        """
        Flag a review for moderation.
        """
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return {'success': False, 'error': 'Review not found'}
        
        review.is_flagged = True
        review.save()
        
        # In production, create a moderation ticket
        
        return {
            'success': True,
            'message': 'Review flagged for moderation'
        }
