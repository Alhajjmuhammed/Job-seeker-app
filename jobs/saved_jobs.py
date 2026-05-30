"""
Saved jobs functionality for Worker Connect.

Allows workers to save jobs for later viewing.
"""

from django.db.models import Count
from django.utils import timezone
from typing import Dict, Any, List


class SavedJobsService:
    """
    Service for managing saved jobs.
    """
    
    @staticmethod
    def save_job(worker_profile, job) -> Dict[str, Any]:
        """
        Save a job for later viewing.
        """
        from jobs.models import SavedJob
        
        # Check if already saved
        existing = SavedJob.objects.filter(
            worker=worker_profile,
            job=job
        ).first()
        
        if existing:
            return {
                'success': True,
                'already_saved': True,
                'saved_at': existing.created_at.isoformat(),
                'message': 'Job was already saved'
            }
        
        # Create saved job
        saved = SavedJob.objects.create(
            worker=worker_profile,
            job=job
        )
        
        return {
            'success': True,
            'saved_id': saved.id,
            'job_id': job.id,
            'saved_at': saved.created_at.isoformat(),
            'message': 'Job saved successfully'
        }
    
    @staticmethod
    def unsave_job(worker_profile, job) -> Dict[str, Any]:
        """
        Remove a job from saved list.
        """
        from jobs.models import SavedJob
        
        deleted_count, _ = SavedJob.objects.filter(
            worker=worker_profile,
            job=job
        ).delete()
        
        if deleted_count == 0:
            return {
                'success': False,
                'error': 'Job was not in saved list'
            }
        
        return {
            'success': True,
            'job_id': job.id,
            'message': 'Job removed from saved list'
        }
    
    @staticmethod
    def get_saved_jobs(
        worker_profile,
        include_closed: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all saved jobs for a worker.
        """
        from jobs.models import SavedJob
        
        queryset = SavedJob.objects.filter(
            worker=worker_profile
        ).select_related(
            'job__client__user'
        ).order_by('-created_at')
        
        if not include_closed:
            queryset = queryset.filter(job__status='open')
        
        saved_jobs = []
        for saved in queryset[:limit]:
            job = saved.job
            saved_jobs.append({
                'saved_id': saved.id,
                'saved_at': saved.created_at.isoformat(),
                'job': {
                    'id': job.id,
                    'title': job.title,
                    'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
                    'status': job.status,
                    'location': getattr(job, 'location', ''),
                    'budget': str(job.budget) if hasattr(job, 'budget') and job.budget else None,
                    'client_name': job.client.user.get_full_name() or job.client.user.username,
                    'created_at': job.created_at.isoformat(),
                },
                'is_available': job.status == 'open',
            })
        
        return saved_jobs
    
    @staticmethod
    def is_saved(worker_profile, job) -> bool:
        """
        Check if a job is saved by a worker.
        """
        from jobs.models import SavedJob
        
        return SavedJob.objects.filter(
            worker=worker_profile,
            job=job
        ).exists()
    
    @staticmethod
    def get_saved_count(worker_profile) -> int:
        """
        Get count of saved jobs.
        """
        from jobs.models import SavedJob
        
        return SavedJob.objects.filter(
            worker=worker_profile
        ).count()
    
    @staticmethod
    def clear_unavailable(worker_profile) -> Dict[str, Any]:
        """
        Remove jobs that are no longer available.
        """
        from jobs.models import SavedJob
        
        deleted_count, _ = SavedJob.objects.filter(
            worker=worker_profile
        ).exclude(
            job__status='open'
        ).delete()
        
        return {
            'success': True,
            'removed_count': deleted_count,
            'message': f'Removed {deleted_count} unavailable jobs from saved list'
        }
