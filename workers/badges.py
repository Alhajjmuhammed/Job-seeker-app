"""
Worker verification badges and tiers for Worker Connect.

Manages verification levels and badges for workers.
"""

from django.db import models
from django.utils import timezone
from typing import Dict, Any, List


class VerificationBadge(models.Model):
    """
    Badge types that workers can earn.
    """
    
    BADGE_TYPE_CHOICES = [
        ('identity_verified', 'Identity Verified'),
        ('background_check', 'Background Check'),
        ('skill_certified', 'Skill Certified'),
        ('top_rated', 'Top Rated'),
        ('fast_responder', 'Fast Responder'),
        ('reliability', 'Reliability Badge'),
        ('veteran', 'Veteran Worker'),
        ('premium', 'Premium Member'),
    ]
    
    name = models.CharField(max_length=50)
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPE_CHOICES, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)  # Icon name/class
    color = models.CharField(max_length=20, default='#007bff')
    
    # Requirements
    requirements = models.TextField(blank=True, help_text="Human-readable requirements")
    auto_award = models.BooleanField(default=False, help_text="Automatically awarded when criteria met")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WorkerBadge(models.Model):
    """
    Badges earned by workers.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='badges'
    )
    badge = models.ForeignKey(
        VerificationBadge,
        on_delete=models.CASCADE,
        related_name='awards'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Verification info
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='badges_verified'
    )
    verification_notes = models.TextField(blank=True)
    verification_document = models.FileField(
        upload_to='badge_verifications/',
        null=True, blank=True
    )
    
    # Validity
    issued_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issued_at']
        unique_together = ['worker', 'badge']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.badge.name}"
    
    @property
    def is_valid(self):
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class VerificationTier(models.Model):
    """
    Verification tier levels for workers.
    """
    
    name = models.CharField(max_length=50)
    level = models.PositiveIntegerField(unique=True)  # 1, 2, 3, etc.
    description = models.TextField()
    
    # Requirements
    min_reviews = models.PositiveIntegerField(default=0)
    min_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    min_completed_jobs = models.PositiveIntegerField(default=0)
    required_badges = models.ManyToManyField(
        VerificationBadge,
        blank=True,
        related_name='required_for_tiers'
    )
    
    # Benefits
    benefits = models.TextField(blank=True, help_text="JSON list of benefits")
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=10.00,
        help_text="Platform commission percentage"
    )
    priority_in_search = models.BooleanField(default=False)
    
    # Appearance
    badge_color = models.CharField(max_length=20, default='#6c757d')
    icon = models.CharField(max_length=50, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['level']
    
    def __str__(self):
        return f"Tier {self.level}: {self.name}"


class BadgeService:
    """
    Service for managing badges and verification.
    """
    
    @staticmethod
    def apply_for_badge(worker_profile, badge_type: str, document=None) -> Dict[str, Any]:
        """
        Apply for a verification badge.
        """
        try:
            badge = VerificationBadge.objects.get(
                badge_type=badge_type,
                is_active=True
            )
        except VerificationBadge.DoesNotExist:
            return {'success': False, 'error': 'Badge type not found'}
        
        # Check if already has badge
        existing = WorkerBadge.objects.filter(
            worker=worker_profile,
            badge=badge
        ).first()
        
        if existing:
            if existing.status == 'active':
                return {'success': False, 'error': 'You already have this badge'}
            elif existing.status == 'pending':
                return {'success': False, 'error': 'Application already pending'}
        
        # Create application
        worker_badge = WorkerBadge.objects.create(
            worker=worker_profile,
            badge=badge,
            status='pending',
            verification_document=document
        )
        
        return {
            'success': True,
            'application_id': worker_badge.id,
            'badge_name': badge.name,
            'message': 'Badge application submitted for review'
        }
    
    @staticmethod
    def verify_badge(
        worker_badge_id: int,
        admin_user,
        approve: bool,
        notes: str = '',
        expires_in_days: int = None
    ) -> Dict[str, Any]:
        """
        Admin verifies or rejects a badge application.
        """
        try:
            worker_badge = WorkerBadge.objects.get(id=worker_badge_id)
        except WorkerBadge.DoesNotExist:
            return {'success': False, 'error': 'Badge application not found'}
        
        if approve:
            worker_badge.status = 'active'
            worker_badge.issued_at = timezone.now()
            if expires_in_days:
                worker_badge.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        else:
            worker_badge.status = 'revoked'
        
        worker_badge.verified_by = admin_user
        worker_badge.verification_notes = notes
        worker_badge.save()
        
        # Update worker tier if needed
        BadgeService._update_worker_tier(worker_badge.worker)
        
        return {
            'success': True,
            'status': worker_badge.status,
            'message': f'Badge {"approved" if approve else "rejected"}'
        }
    
    @staticmethod
    def _update_worker_tier(worker_profile):
        """
        Update worker's verification tier based on current stats.
        """
        # Get worker's active badges
        active_badges = WorkerBadge.objects.filter(
            worker=worker_profile,
            status='active'
        ).values_list('badge_id', flat=True)
        
        # Get worker stats
        completed_jobs = getattr(worker_profile, 'completed_jobs_count', 0)
        rating = getattr(worker_profile, 'average_rating', 0) or 0
        reviews = getattr(worker_profile, 'total_reviews', 0) or 0
        
        # Find highest eligible tier
        eligible_tier = None
        tiers = VerificationTier.objects.filter(is_active=True).order_by('-level')
        
        for tier in tiers:
            # Check requirements
            if reviews < tier.min_reviews:
                continue
            if rating < float(tier.min_rating):
                continue
            if completed_jobs < tier.min_completed_jobs:
                continue
            
            # Check required badges
            required_badges = set(tier.required_badges.values_list('id', flat=True))
            if not required_badges.issubset(set(active_badges)):
                continue
            
            eligible_tier = tier
            break
        
        # Update worker tier
        if eligible_tier:
            worker_profile.verification_tier = eligible_tier.level
            worker_profile.save()
    
    @staticmethod
    def get_worker_badges(worker_profile) -> List[Dict[str, Any]]:
        """
        Get all badges for a worker.
        """
        badges = WorkerBadge.objects.filter(
            worker=worker_profile
        ).select_related('badge')
        
        result = []
        for wb in badges:
            result.append({
                'id': wb.id,
                'badge': {
                    'name': wb.badge.name,
                    'type': wb.badge.badge_type,
                    'description': wb.badge.description,
                    'icon': wb.badge.icon,
                    'color': wb.badge.color,
                },
                'status': wb.status,
                'is_valid': wb.is_valid,
                'issued_at': wb.issued_at.isoformat() if wb.issued_at else None,
                'expires_at': wb.expires_at.isoformat() if wb.expires_at else None,
            })
        
        return result
    
    @staticmethod
    def get_available_badges(worker_profile) -> List[Dict[str, Any]]:
        """
        Get badges that worker can apply for.
        """
        # Get badges worker already has or applied for
        existing = WorkerBadge.objects.filter(
            worker=worker_profile,
            status__in=['active', 'pending']
        ).values_list('badge_id', flat=True)
        
        available = VerificationBadge.objects.filter(
            is_active=True
        ).exclude(id__in=existing)
        
        result = []
        for badge in available:
            result.append({
                'type': badge.badge_type,
                'name': badge.name,
                'description': badge.description,
                'requirements': badge.requirements,
            })
        
        return result
    
    @staticmethod
    def check_auto_badges(worker_profile):
        """
        Check and award automatic badges.
        """
        auto_badges = VerificationBadge.objects.filter(
            is_active=True,
            auto_award=True
        )
        
        for badge in auto_badges:
            # Skip if already has
            if WorkerBadge.objects.filter(
                worker=worker_profile,
                badge=badge,
                status='active'
            ).exists():
                continue
            
            # Check criteria based on badge type
            should_award = False
            
            if badge.badge_type == 'top_rated':
                rating = getattr(worker_profile, 'average_rating', 0) or 0
                reviews = getattr(worker_profile, 'total_reviews', 0) or 0
                should_award = rating >= 4.8 and reviews >= 10
            
            elif badge.badge_type == 'veteran':
                completed = getattr(worker_profile, 'completed_jobs_count', 0)
                should_award = completed >= 50
            
            elif badge.badge_type == 'reliability':
                # Check completion rate
                completed = getattr(worker_profile, 'completed_jobs_count', 0)
                cancelled = getattr(worker_profile, 'cancelled_jobs_count', 0)
                if completed + cancelled > 10:
                    completion_rate = completed / (completed + cancelled)
                    should_award = completion_rate >= 0.95
            
            if should_award:
                WorkerBadge.objects.create(
                    worker=worker_profile,
                    badge=badge,
                    status='active',
                    issued_at=timezone.now()
                )
