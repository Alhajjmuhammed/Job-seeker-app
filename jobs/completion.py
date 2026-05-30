"""
Job completion workflow for Worker Connect.

Handles the job completion process including reviews, ratings, and disputes.
"""

from django.db.models import Avg
from django.utils import timezone
from typing import Dict, Any, Optional
from decimal import Decimal


class JobCompletionService:
    """
    Service for managing job completion workflow.
    """
    
    COMPLETION_STATES = [
        'in_progress',
        'work_submitted',
        'revision_requested',
        'completed',
        'disputed',
        'cancelled',
    ]
    
    @staticmethod
    def submit_work(job, worker_profile, notes: str = '') -> Dict[str, Any]:
        """
        Worker submits completed work for review.
        """
        from jobs.models import JobApplication
        
        # Verify worker is assigned to job
        application = JobApplication.objects.filter(
            job_request=job,
            worker=worker_profile,
            status='accepted'
        ).first()
        
        if not application:
            return {
                'success': False,
                'error': 'You are not assigned to this job'
            }
        
        if job.status not in ['open', 'in_progress']:
            return {
                'success': False,
                'error': f'Cannot submit work for job in {job.status} status'
            }
        
        # Update job status
        job.status = 'pending_review'
        job.save()
        
        # Log the submission
        # In production, create a JobUpdate model to track these
        
        return {
            'success': True,
            'job_id': job.id,
            'status': 'pending_review',
            'message': 'Work submitted for client review'
        }
    
    @staticmethod
    def approve_completion(job, client_profile, rating: int = None, review: str = '') -> Dict[str, Any]:
        """
        Client approves job completion.
        """
        # Verify client owns job
        if job.client != client_profile:
            return {
                'success': False,
                'error': 'You are not the owner of this job'
            }
        
        if job.status != 'pending_review':
            return {
                'success': False,
                'error': 'Job is not pending review'
            }
        
        # Get the accepted application
        from jobs.models import JobApplication
        application = JobApplication.objects.filter(
            job_request=job,
            status='accepted'
        ).first()
        
        if not application:
            return {
                'success': False,
                'error': 'No worker assigned to this job'
            }
        
        # Complete the job
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()
        
        # Create review if provided
        if rating:
            # Store review (would use a Review model in production)
            worker = application.worker
            if hasattr(worker, 'total_ratings'):
                worker.total_ratings = (worker.total_ratings or 0) + 1
                worker.rating_sum = (worker.rating_sum or 0) + rating
                worker.average_rating = worker.rating_sum / worker.total_ratings
                worker.save()
        
        return {
            'success': True,
            'job_id': job.id,
            'status': 'completed',
            'message': 'Job marked as completed'
        }
    
    @staticmethod
    def request_revision(job, client_profile, reason: str) -> Dict[str, Any]:
        """
        Client requests revision on submitted work.
        """
        if job.client != client_profile:
            return {
                'success': False,
                'error': 'You are not the owner of this job'
            }
        
        if job.status != 'pending_review':
            return {
                'success': False,
                'error': 'Job is not pending review'
            }
        
        # Update job status
        job.status = 'in_progress'  # Back to in progress
        job.save()
        
        # Create revision request notification
        # Would trigger notification to worker
        
        return {
            'success': True,
            'job_id': job.id,
            'status': 'in_progress',
            'message': 'Revision requested',
            'reason': reason
        }
    
    @staticmethod
    def open_dispute(job, user, reason: str, details: str = '') -> Dict[str, Any]:
        """
        Open a dispute for a job.
        """
        from jobs.models import JobApplication
        
        # Verify user is involved in job
        is_client = (job.client.user == user)
        is_worker = JobApplication.objects.filter(
            job_request=job,
            worker__user=user,
            status='accepted'
        ).exists()
        
        if not is_client and not is_worker:
            return {
                'success': False,
                'error': 'You are not involved in this job'
            }
        
        if job.status == 'disputed':
            return {
                'success': False,
                'error': 'Job is already in dispute'
            }
        
        # Update job status
        previous_status = job.status
        job.status = 'disputed'
        job.save()
        
        # Create dispute record (would use Dispute model in production)
        dispute_data = {
            'job_id': job.id,
            'opened_by': 'client' if is_client else 'worker',
            'reason': reason,
            'details': details,
            'previous_status': previous_status,
            'opened_at': timezone.now().isoformat(),
        }
        
        return {
            'success': True,
            'job_id': job.id,
            'status': 'disputed',
            'dispute': dispute_data,
            'message': 'Dispute opened. Admin will review.'
        }
    
    @staticmethod
    def resolve_dispute(job, admin_user, resolution: str, favor: str, notes: str = '') -> Dict[str, Any]:
        """
        Admin resolves a dispute.
        
        Args:
            job: JobRequest instance
            admin_user: Admin user resolving
            resolution: 'complete', 'cancel', 'partial_refund'
            favor: 'client', 'worker', 'split'
            notes: Admin notes
        """
        if not admin_user.is_staff:
            return {
                'success': False,
                'error': 'Only admins can resolve disputes'
            }
        
        if job.status != 'disputed':
            return {
                'success': False,
                'error': 'Job is not in dispute'
            }
        
        # Apply resolution
        if resolution == 'complete':
            job.status = 'completed'
            job.completed_at = timezone.now()
        elif resolution == 'cancel':
            job.status = 'cancelled'
        else:
            job.status = 'completed'  # Partial refund still marks complete
        
        job.save()
        
        return {
            'success': True,
            'job_id': job.id,
            'resolution': resolution,
            'favor': favor,
            'final_status': job.status,
            'message': f'Dispute resolved in favor of {favor}'
        }
    
    @staticmethod
    def cancel_job(job, user, reason: str = '') -> Dict[str, Any]:
        """
        Cancel a job.
        """
        from jobs.models import JobApplication
        
        is_client = (job.client.user == user)
        
        if not is_client and not user.is_staff:
            return {
                'success': False,
                'error': 'Only job owner or admin can cancel'
            }
        
        if job.status in ['completed', 'cancelled']:
            return {
                'success': False,
                'error': f'Cannot cancel job in {job.status} status'
            }
        
        # Check if work has started
        has_accepted_application = JobApplication.objects.filter(
            job_request=job,
            status='accepted'
        ).exists()
        
        # Update status
        job.status = 'cancelled'
        job.save()
        
        # Update applications
        JobApplication.objects.filter(
            job_request=job
        ).update(status='cancelled')
        
        return {
            'success': True,
            'job_id': job.id,
            'status': 'cancelled',
            'refund_eligible': not has_accepted_application,
            'message': 'Job cancelled successfully'
        }
    
    @staticmethod
    def get_job_timeline(job) -> list:
        """
        Get timeline of job events.
        """
        events = []
        
        # Created
        events.append({
            'event': 'created',
            'timestamp': job.created_at.isoformat(),
            'description': 'Job posted'
        })
        
        # Applications
        from jobs.models import JobApplication
        applications = JobApplication.objects.filter(
            job_request=job
        ).order_by('created_at')
        
        for app in applications:
            events.append({
                'event': 'application',
                'timestamp': app.created_at.isoformat(),
                'description': f'Application from {app.worker.user.get_full_name() or app.worker.user.username}',
                'status': app.status
            })
            
            if app.status == 'accepted':
                events.append({
                    'event': 'worker_assigned',
                    'timestamp': app.updated_at.isoformat() if hasattr(app, 'updated_at') else app.created_at.isoformat(),
                    'description': f'Worker assigned: {app.worker.user.get_full_name() or app.worker.user.username}'
                })
        
        # Completion
        if hasattr(job, 'completed_at') and job.completed_at:
            events.append({
                'event': 'completed',
                'timestamp': job.completed_at.isoformat(),
                'description': 'Job completed'
            })
        
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
