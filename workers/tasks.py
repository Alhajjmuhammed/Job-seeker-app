"""
Celery tasks for workers app.
"""

from celery import shared_task
from django.utils import timezone
from django.db.models import Avg
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_worker_ratings(self):
    """
    Update aggregate ratings for all workers based on reviews.
    """
    try:
        from workers.models import WorkerProfile
        from jobs.reviews import Review
        
        workers = WorkerProfile.objects.all()
        updated_count = 0
        
        for worker in workers:
            reviews = Review.objects.filter(
                reviewee=worker.user,
                is_visible=True
            )
            
            if reviews.exists():
                avg_rating = reviews.aggregate(
                    avg=Avg('overall_rating')
                )['avg']
                
                if avg_rating and worker.rating != avg_rating:
                    worker.rating = round(avg_rating, 2)
                    worker.total_reviews = reviews.count()
                    worker.save(update_fields=['rating', 'total_reviews'])
                    updated_count += 1
        
        logger.info(f"Updated ratings for {updated_count} workers")
        return updated_count
    except Exception as e:
        logger.error(f"Error updating worker ratings: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def check_badge_expirations(self):
    """
    Check for expiring badges and notify workers.
    """
    try:
        from workers.badges import WorkerBadge
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Check badges expiring in 7 days
        expiry_date = timezone.now() + timedelta(days=7)
        
        expiring_badges = WorkerBadge.objects.filter(
            status='active',
            expires_at__lte=expiry_date,
            expires_at__gte=timezone.now()
        ).select_related('worker__user', 'badge')
        
        for worker_badge in expiring_badges:
            # Send expiration warning
            send_mail(
                subject=f"Your {worker_badge.badge.name} badge is expiring soon",
                message=f"Your {worker_badge.badge.name} badge will expire on {worker_badge.expires_at.date()}. Please renew to maintain your verification status.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[worker_badge.worker.user.email],
                fail_silently=True,
            )
        
        # Mark expired badges
        expired = WorkerBadge.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        ).update(status='expired')
        
        logger.info(f"Checked badge expirations: {expiring_badges.count()} expiring soon, {expired} expired")
        return {'expiring': expiring_badges.count(), 'expired': expired}
    except Exception as e:
        logger.error(f"Error checking badge expirations: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def update_worker_stats(self, worker_id):
    """
    Update statistics for a specific worker.
    """
    try:
        from workers.models import WorkerProfile
        from jobs.models import JobRequest
        from jobs.reviews import Review
        from django.db.models import Sum, Count
        
        worker = WorkerProfile.objects.get(id=worker_id)
        
        # Count completed jobs
        completed_jobs = JobRequest.objects.filter(
            assigned_workers=worker,
            status='completed'
        ).count()
        
        # Calculate total earnings
        earnings = JobRequest.objects.filter(
            assigned_workers=worker,
            status='completed'
        ).aggregate(total=Sum('budget'))['total'] or 0
        
        # Get review stats
        reviews = Review.objects.filter(
            reviewee=worker.user,
            is_visible=True
        )
        avg_rating = reviews.aggregate(avg=Avg('overall_rating'))['avg'] or 0
        
        # Update worker profile
        worker.total_jobs_completed = completed_jobs
        worker.total_earnings = earnings
        worker.rating = round(avg_rating, 2)
        worker.total_reviews = reviews.count()
        worker.save(update_fields=[
            'total_jobs_completed', 'total_earnings', 
            'rating', 'total_reviews'
        ])
        
        logger.info(f"Updated stats for worker {worker_id}")
        return {
            'completed_jobs': completed_jobs,
            'earnings': float(earnings),
            'rating': float(avg_rating),
            'reviews': reviews.count(),
        }
    except WorkerProfile.DoesNotExist:
        logger.error(f"Worker {worker_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error updating worker stats: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def check_auto_badges(self, worker_id):
    """
    Check and award automatic badges based on achievements.
    """
    try:
        from workers.models import WorkerProfile
        from workers.badges import BadgeService
        
        worker = WorkerProfile.objects.get(id=worker_id)
        
        # Check for auto-badges
        awarded = BadgeService.check_auto_badges(worker)
        
        logger.info(f"Checked auto badges for worker {worker_id}: {len(awarded)} awarded")
        return awarded
    except WorkerProfile.DoesNotExist:
        logger.error(f"Worker {worker_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error checking auto badges: {e}")
        raise self.retry(exc=e)


@shared_task
def send_welcome_email(user_id, user_type):
    """
    Send welcome email to new user.
    """
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        context = {
            'user': user,
            'is_worker': user_type == 'worker',
            'dashboard_url': f"{settings.FRONTEND_URL}/dashboard",
        }
        
        html_message = render_to_string('emails/welcome.html', context)
        
        send_mail(
            subject="Welcome to Worker Connect!",
            message=f"Welcome to Worker Connect, {user.first_name}! Start exploring opportunities today.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )
        
        logger.info(f"Sent welcome email to {user.email}")
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")


@shared_task
def update_verification_tier(worker_id):
    """
    Update worker's verification tier based on badges.
    """
    try:
        from workers.models import WorkerProfile
        from workers.badges import WorkerBadge, VerificationTier
        
        worker = WorkerProfile.objects.get(id=worker_id)
        
        # Count active badges
        active_badges = WorkerBadge.objects.filter(
            worker=worker,
            status='active'
        ).count()
        
        # Find appropriate tier
        tier = VerificationTier.objects.filter(
            min_badges__lte=active_badges
        ).order_by('-min_badges').first()
        
        if tier:
            # Update worker's tier (if field exists)
            if hasattr(worker, 'verification_tier'):
                worker.verification_tier = tier
                worker.save(update_fields=['verification_tier'])
        
        logger.info(f"Updated verification tier for worker {worker_id}")
        return tier.name if tier else None
    except WorkerProfile.DoesNotExist:
        logger.error(f"Worker {worker_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error updating verification tier: {e}")
        return None
