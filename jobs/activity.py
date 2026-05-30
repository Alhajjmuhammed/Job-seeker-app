"""
Activity feed for Worker Connect dashboard.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Activity(models.Model):
    """
    Activity log for dashboard feeds.
    """
    ACTIVITY_TYPES = [
        # Job activities
        ('job_posted', 'Job Posted'),
        ('job_applied', 'Applied to Job'),
        ('job_assigned', 'Assigned to Job'),
        ('job_started', 'Job Started'),
        ('job_completed', 'Job Completed'),
        ('job_cancelled', 'Job Cancelled'),
        
        # Review activities
        ('review_received', 'Review Received'),
        ('review_given', 'Review Given'),
        
        # Badge activities
        ('badge_earned', 'Badge Earned'),
        ('verification_completed', 'Verification Completed'),
        
        # Invoice activities
        ('invoice_sent', 'Invoice Sent'),
        ('invoice_paid', 'Invoice Paid'),
        
        # Payment activities
        ('payment_received', 'Payment Received'),
        ('payment_sent', 'Payment Sent'),
        
        # Profile activities
        ('profile_updated', 'Profile Updated'),
        ('portfolio_added', 'Portfolio Item Added'),
        
        # Message activities
        ('message_received', 'Message Received'),
        
        # System activities
        ('account_created', 'Account Created'),
        ('subscription_updated', 'Subscription Updated'),
    ]
    
    # User who performed or receives the activity
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Generic relation to any related object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Read status
    is_read = models.BooleanField(default=False)
    
    # Visibility
    is_public = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activities'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.title}"


class ActivityService:
    """
    Service class for managing activity feeds.
    """
    
    @staticmethod
    def log_activity(user, activity_type, title, description='',
                     related_object=None, metadata=None, is_public=False):
        """
        Log an activity for a user.
        """
        activity_data = {
            'user': user,
            'activity_type': activity_type,
            'title': title,
            'description': description,
            'metadata': metadata or {},
            'is_public': is_public,
        }
        
        if related_object:
            activity_data['content_type'] = ContentType.objects.get_for_model(related_object)
            activity_data['object_id'] = related_object.pk
        
        return Activity.objects.create(**activity_data)
    
    @staticmethod
    def get_user_feed(user, limit=50, activity_types=None, unread_only=False):
        """
        Get activity feed for a user.
        """
        queryset = Activity.objects.filter(user=user)
        
        if activity_types:
            queryset = queryset.filter(activity_type__in=activity_types)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        return queryset[:limit]
    
    @staticmethod
    def get_public_feed(limit=20, activity_types=None):
        """
        Get public activity feed (for community/discover features).
        """
        queryset = Activity.objects.filter(is_public=True)
        
        if activity_types:
            queryset = queryset.filter(activity_type__in=activity_types)
        
        return queryset[:limit]
    
    @staticmethod
    def mark_as_read(activity_id, user):
        """
        Mark an activity as read.
        """
        return Activity.objects.filter(
            id=activity_id,
            user=user
        ).update(is_read=True)
    
    @staticmethod
    def mark_all_as_read(user, activity_types=None):
        """
        Mark all activities as read.
        """
        queryset = Activity.objects.filter(user=user, is_read=False)
        
        if activity_types:
            queryset = queryset.filter(activity_type__in=activity_types)
        
        return queryset.update(is_read=True)
    
    @staticmethod
    def get_unread_count(user):
        """
        Get count of unread activities.
        """
        return Activity.objects.filter(user=user, is_read=False).count()
    
    @staticmethod
    def delete_old_activities(days=90):
        """
        Delete activities older than specified days.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return Activity.objects.filter(created_at__lt=cutoff).delete()
    
    # Convenience methods for common activities
    
    @staticmethod
    def log_job_posted(job):
        """Log job posted activity."""
        return ActivityService.log_activity(
            user=job.client.user,
            activity_type='job_posted',
            title=f'Posted new job: {job.title}',
            description=job.description[:200] if job.description else '',
            related_object=job,
            is_public=True,
        )
    
    @staticmethod
    def log_job_applied(application):
        """Log job application activity."""
        return ActivityService.log_activity(
            user=application.worker.user,
            activity_type='job_applied',
            title=f'Applied to job: {application.job.title}',
            related_object=application.job,
        )
    
    @staticmethod
    def log_job_assigned(job, worker):
        """Log job assignment activity."""
        return ActivityService.log_activity(
            user=worker.user,
            activity_type='job_assigned',
            title=f'Assigned to job: {job.title}',
            related_object=job,
        )
    
    @staticmethod
    def log_job_completed(job, worker):
        """Log job completion activity."""
        return ActivityService.log_activity(
            user=worker.user,
            activity_type='job_completed',
            title=f'Completed job: {job.title}',
            related_object=job,
            is_public=True,
        )
    
    @staticmethod
    def log_review_received(review):
        """Log review received activity."""
        return ActivityService.log_activity(
            user=review.reviewee,
            activity_type='review_received',
            title=f'Received {review.overall_rating}-star review',
            metadata={'rating': review.overall_rating},
            related_object=review,
        )
    
    @staticmethod
    def log_badge_earned(worker_badge):
        """Log badge earned activity."""
        return ActivityService.log_activity(
            user=worker_badge.worker.user,
            activity_type='badge_earned',
            title=f'Earned badge: {worker_badge.badge.display_name}',
            related_object=worker_badge,
            is_public=True,
        )
    
    @staticmethod
    def log_payment_received(payment, worker):
        """Log payment received activity."""
        return ActivityService.log_activity(
            user=worker.user,
            activity_type='payment_received',
            title=f'Received payment of ${payment.amount}',
            metadata={'amount': str(payment.amount)},
            related_object=payment,
        )
