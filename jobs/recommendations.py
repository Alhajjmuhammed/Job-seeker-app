"""
Job recommendation engine for Worker Connect.

Recommends jobs to workers based on skills, location, history, and preferences.
"""

from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Any, Optional
import math


class RecommendationEngine:
    """
    Multi-factor recommendation engine for matching workers to jobs.
    """
    
    # Scoring weights
    WEIGHT_SKILL_MATCH = 0.35
    WEIGHT_LOCATION = 0.25
    WEIGHT_HISTORY = 0.20
    WEIGHT_AVAILABILITY = 0.15
    WEIGHT_FRESHNESS = 0.05
    
    @classmethod
    def get_recommendations(
        cls,
        worker_profile,
        limit: int = 20,
        include_scores: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get job recommendations for a worker.
        
        Args:
            worker_profile: WorkerProfile instance
            limit: Maximum number of recommendations
            include_scores: Include detailed scoring breakdown
            
        Returns:
            List of recommended jobs with scores
        """
        from jobs.models import JobRequest
        from workers.availability import AvailabilityService
        
        # Get active jobs that worker hasn't applied to
        applied_job_ids = worker_profile.applications.values_list('job_request_id', flat=True)
        
        jobs = JobRequest.objects.filter(
            status='open'
        ).exclude(
            id__in=applied_job_ids
        ).select_related('client', 'client__user')
        
        # Score each job
        scored_jobs = []
        for job in jobs:
            score_details = cls._calculate_job_score(worker_profile, job)
            scored_jobs.append({
                'job': job,
                'score': score_details['total_score'],
                'score_details': score_details if include_scores else None,
            })
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top N
        return scored_jobs[:limit]
    
    @classmethod
    def _calculate_job_score(cls, worker_profile, job) -> Dict[str, Any]:
        """Calculate overall match score for a job."""
        skill_score = cls._calculate_skill_score(worker_profile, job)
        location_score = cls._calculate_location_score(worker_profile, job)
        history_score = cls._calculate_history_score(worker_profile, job)
        availability_score = cls._calculate_availability_score(worker_profile, job)
        freshness_score = cls._calculate_freshness_score(job)
        
        total_score = (
            skill_score * cls.WEIGHT_SKILL_MATCH +
            location_score * cls.WEIGHT_LOCATION +
            history_score * cls.WEIGHT_HISTORY +
            availability_score * cls.WEIGHT_AVAILABILITY +
            freshness_score * cls.WEIGHT_FRESHNESS
        )
        
        return {
            'total_score': round(total_score, 3),
            'skill_score': round(skill_score, 3),
            'location_score': round(location_score, 3),
            'history_score': round(history_score, 3),
            'availability_score': round(availability_score, 3),
            'freshness_score': round(freshness_score, 3),
        }
    
    @classmethod
    def _calculate_skill_score(cls, worker_profile, job) -> float:
        """
        Calculate skill match score (0-1).
        
        Compares worker skills with job requirements.
        """
        # Get worker skills
        worker_skills = set(
            s.lower() for s in worker_profile.skills.split(',') if s.strip()
        ) if worker_profile.skills else set()
        
        # Extract skills from job title and description
        job_text = f"{job.title} {job.description}".lower()
        
        if not worker_skills:
            return 0.3  # Base score for workers without listed skills
        
        # Count matching skills
        matches = 0
        for skill in worker_skills:
            skill = skill.strip()
            if skill and skill in job_text:
                matches += 1
        
        if len(worker_skills) == 0:
            return 0.3
        
        # Calculate match percentage
        match_ratio = matches / len(worker_skills)
        
        # Bonus for exact category match
        if hasattr(job, 'job_type') and hasattr(worker_profile, 'primary_skill'):
            if job.job_type and worker_profile.primary_skill:
                if job.job_type.lower() == worker_profile.primary_skill.lower():
                    match_ratio = min(1.0, match_ratio + 0.3)
        
        return min(1.0, match_ratio)
    
    @classmethod
    def _calculate_location_score(cls, worker_profile, job) -> float:
        """
        Calculate location proximity score (0-1).
        
        Closer jobs get higher scores.
        """
        # Check if both have location data
        worker_lat = getattr(worker_profile, 'latitude', None)
        worker_lng = getattr(worker_profile, 'longitude', None)
        job_lat = getattr(job, 'latitude', None)
        job_lng = getattr(job, 'longitude', None)
        
        if not all([worker_lat, worker_lng, job_lat, job_lng]):
            # Fall back to city/location text matching
            worker_location = getattr(worker_profile, 'location', '') or ''
            job_location = getattr(job, 'location', '') or ''
            
            if worker_location.lower() == job_location.lower() and worker_location:
                return 1.0
            elif worker_location.lower() in job_location.lower() or job_location.lower() in worker_location.lower():
                return 0.7
            else:
                return 0.3
        
        # Calculate distance using Haversine formula
        distance = cls._haversine_distance(
            worker_lat, worker_lng, job_lat, job_lng
        )
        
        # Convert distance to score (closer = higher)
        # 0-5 km: 1.0, 5-10 km: 0.8, 10-25 km: 0.6, 25-50 km: 0.4, 50+ km: 0.2
        max_distance = getattr(worker_profile, 'max_travel_distance', 50) or 50
        
        if distance <= 5:
            return 1.0
        elif distance <= 10:
            return 0.8
        elif distance <= 25:
            return 0.6
        elif distance <= max_distance:
            return 0.4
        else:
            return 0.2
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @classmethod
    def _calculate_history_score(cls, worker_profile, job) -> float:
        """
        Calculate history-based score (0-1).
        
        Based on worker's past applications and success rate.
        """
        from jobs.models import JobApplication
        
        # Get worker's application history
        applications = JobApplication.objects.filter(
            worker=worker_profile
        ).select_related('job_request')
        
        if not applications.exists():
            return 0.5  # Neutral score for new workers
        
        # Calculate success metrics
        total_apps = applications.count()
        accepted_apps = applications.filter(status='accepted').count()
        
        success_rate = accepted_apps / total_apps if total_apps > 0 else 0
        
        # Check if worker has completed similar jobs
        similar_job_score = 0
        completed_jobs = applications.filter(status='accepted')
        
        job_title_words = set(job.title.lower().split())
        
        for app in completed_jobs:
            past_job_words = set(app.job_request.title.lower().split())
            overlap = len(job_title_words & past_job_words)
            if overlap > 0:
                similar_job_score = max(similar_job_score, overlap / len(job_title_words))
        
        # Combine success rate and similarity
        return (success_rate * 0.5 + similar_job_score * 0.5)
    
    @classmethod
    def _calculate_availability_score(cls, worker_profile, job) -> float:
        """
        Calculate availability score (0-1).
        
        Higher score if worker is likely available when job needs to be done.
        """
        from workers.availability import RecurringAvailability
        
        # Check if worker has any availability set
        has_availability = RecurringAvailability.objects.filter(
            worker=worker_profile,
            is_active=True
        ).exists()
        
        if not has_availability:
            return 0.5  # Unknown availability
        
        # Get availability count
        availability_count = RecurringAvailability.objects.filter(
            worker=worker_profile,
            is_active=True
        ).count()
        
        # More availability = higher score
        return min(1.0, availability_count / 5)
    
    @classmethod
    def _calculate_freshness_score(cls, job) -> float:
        """
        Calculate job freshness score (0-1).
        
        Newer jobs get higher scores.
        """
        age = timezone.now() - job.created_at
        
        if age < timedelta(hours=24):
            return 1.0
        elif age < timedelta(days=3):
            return 0.8
        elif age < timedelta(days=7):
            return 0.6
        elif age < timedelta(days=14):
            return 0.4
        else:
            return 0.2
    
    @classmethod
    def get_worker_recommendations(
        cls,
        client_profile,
        job,
        limit: int = 20,
        include_scores: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get worker recommendations for a job (for clients).
        
        Args:
            client_profile: ClientProfile instance
            job: JobRequest instance
            limit: Maximum number of recommendations
            include_scores: Include detailed scoring breakdown
            
        Returns:
            List of recommended workers with scores
        """
        from workers.models import WorkerProfile
        
        # Get workers who haven't applied
        applied_worker_ids = job.applications.values_list('worker_id', flat=True)
        
        workers = WorkerProfile.objects.filter(
            is_verified=True
        ).exclude(
            id__in=applied_worker_ids
        ).select_related('user')
        
        # Score each worker
        scored_workers = []
        for worker in workers:
            score_details = cls._calculate_worker_score(worker, job)
            scored_workers.append({
                'worker': worker,
                'score': score_details['total_score'],
                'score_details': score_details if include_scores else None,
            })
        
        # Sort by score descending
        scored_workers.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_workers[:limit]
    
    @classmethod
    def _calculate_worker_score(cls, worker_profile, job) -> Dict[str, Any]:
        """Calculate overall match score for a worker."""
        skill_score = cls._calculate_skill_score(worker_profile, job)
        location_score = cls._calculate_location_score(worker_profile, job)
        history_score = cls._calculate_history_score(worker_profile, job)
        availability_score = cls._calculate_availability_score(worker_profile, job)
        
        # Workers also get rating score
        rating_score = cls._calculate_rating_score(worker_profile)
        
        total_score = (
            skill_score * 0.30 +
            location_score * 0.25 +
            history_score * 0.20 +
            availability_score * 0.10 +
            rating_score * 0.15
        )
        
        return {
            'total_score': round(total_score, 3),
            'skill_score': round(skill_score, 3),
            'location_score': round(location_score, 3),
            'history_score': round(history_score, 3),
            'availability_score': round(availability_score, 3),
            'rating_score': round(rating_score, 3),
        }
    
    @classmethod
    def _calculate_rating_score(cls, worker_profile) -> float:
        """Calculate rating score (0-1)."""
        rating = getattr(worker_profile, 'average_rating', None)
        
        if rating is None:
            return 0.5  # Neutral for unrated workers
        
        # Convert 1-5 rating to 0-1 score
        return rating / 5.0
