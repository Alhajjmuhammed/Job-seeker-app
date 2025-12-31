"""
Earnings tracking system for Worker Connect.

Tracks worker earnings, payments, and financial reports.
"""

from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional


class EarningsService:
    """
    Service for tracking and reporting worker earnings.
    """
    
    @staticmethod
    def get_earnings_summary(
        worker_profile,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
    ) -> Dict[str, Any]:
        """
        Get earnings summary for a worker.
        
        Args:
            worker_profile: WorkerProfile instance
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: today)
        """
        from jobs.models import JobApplication
        
        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date()
        if not end_date:
            end_date = timezone.now().date()
        
        # Get completed jobs in period
        completed_jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
            job_request__status='completed',
        ).select_related('job_request')
        
        # Filter by date if job has completion date
        # For now, use created_at as proxy
        completed_jobs = completed_jobs.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Calculate totals
        total_jobs = completed_jobs.count()
        
        # Calculate earnings (assume job budget is the payment)
        total_earnings = Decimal('0.00')
        for app in completed_jobs:
            if hasattr(app.job_request, 'budget') and app.job_request.budget:
                total_earnings += Decimal(str(app.job_request.budget))
        
        # Get pending payments (accepted but not completed)
        pending_jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
        ).exclude(
            job_request__status='completed'
        )
        
        pending_earnings = Decimal('0.00')
        for app in pending_jobs:
            if hasattr(app.job_request, 'budget') and app.job_request.budget:
                pending_earnings += Decimal(str(app.job_request.budget))
        
        # Calculate average per job
        avg_per_job = total_earnings / total_jobs if total_jobs > 0 else Decimal('0.00')
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'earnings': {
                'total': str(total_earnings),
                'pending': str(pending_earnings),
                'average_per_job': str(avg_per_job.quantize(Decimal('0.01'))),
            },
            'jobs': {
                'completed': total_jobs,
                'pending': pending_jobs.count(),
            },
        }
    
    @staticmethod
    def get_earnings_breakdown(
        worker_profile,
        group_by: str = 'month',
        periods: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get earnings breakdown by time period.
        
        Args:
            worker_profile: WorkerProfile instance
            group_by: 'day', 'week', or 'month'
            periods: Number of periods to include
        """
        from jobs.models import JobApplication
        
        breakdown = []
        now = timezone.now()
        
        for i in range(periods):
            if group_by == 'day':
                period_end = (now - timedelta(days=i)).date()
                period_start = period_end
                label = period_end.strftime('%Y-%m-%d')
            elif group_by == 'week':
                period_end = (now - timedelta(weeks=i)).date()
                period_start = period_end - timedelta(days=6)
                label = f"Week of {period_start.strftime('%Y-%m-%d')}"
            else:  # month
                period_end = (now - timedelta(days=30*i)).date()
                period_start = period_end - timedelta(days=29)
                label = period_end.strftime('%Y-%m')
            
            # Get jobs for period
            jobs = JobApplication.objects.filter(
                worker=worker_profile,
                status='accepted',
                job_request__status='completed',
                created_at__date__gte=period_start,
                created_at__date__lte=period_end,
            ).select_related('job_request')
            
            # Calculate earnings
            earnings = Decimal('0.00')
            for app in jobs:
                if hasattr(app.job_request, 'budget') and app.job_request.budget:
                    earnings += Decimal(str(app.job_request.budget))
            
            breakdown.append({
                'period': label,
                'start_date': period_start.isoformat(),
                'end_date': period_end.isoformat(),
                'earnings': str(earnings),
                'jobs_count': jobs.count(),
            })
        
        # Reverse to show oldest first
        breakdown.reverse()
        
        return breakdown
    
    @staticmethod
    def get_earnings_by_category(worker_profile) -> List[Dict[str, Any]]:
        """
        Get earnings breakdown by job category/type.
        """
        from jobs.models import JobApplication
        
        # Get all completed jobs
        jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
            job_request__status='completed',
        ).select_related('job_request')
        
        # Group by job type (extracted from title/category)
        category_earnings = {}
        
        for app in jobs:
            # Use job type if available, otherwise extract from title
            category = getattr(app.job_request, 'job_type', None)
            if not category:
                # Simple extraction from title
                title_words = app.job_request.title.lower().split()
                category = title_words[0] if title_words else 'other'
            
            category = category.title()
            
            if category not in category_earnings:
                category_earnings[category] = {
                    'earnings': Decimal('0.00'),
                    'count': 0,
                }
            
            if hasattr(app.job_request, 'budget') and app.job_request.budget:
                category_earnings[category]['earnings'] += Decimal(str(app.job_request.budget))
            category_earnings[category]['count'] += 1
        
        # Convert to list
        result = []
        for category, data in category_earnings.items():
            result.append({
                'category': category,
                'earnings': str(data['earnings']),
                'jobs_count': data['count'],
                'avg_per_job': str(
                    (data['earnings'] / data['count']).quantize(Decimal('0.01'))
                ) if data['count'] > 0 else '0.00',
            })
        
        # Sort by earnings descending
        result.sort(key=lambda x: Decimal(x['earnings']), reverse=True)
        
        return result
    
    @staticmethod
    def get_top_clients(worker_profile, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top clients by earnings.
        """
        from jobs.models import JobApplication
        
        # Get all completed jobs
        jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
            job_request__status='completed',
        ).select_related('job_request__client__user')
        
        # Group by client
        client_earnings = {}
        
        for app in jobs:
            client = app.job_request.client
            client_id = client.id
            
            if client_id not in client_earnings:
                client_earnings[client_id] = {
                    'client': client,
                    'earnings': Decimal('0.00'),
                    'jobs_count': 0,
                }
            
            if hasattr(app.job_request, 'budget') and app.job_request.budget:
                client_earnings[client_id]['earnings'] += Decimal(str(app.job_request.budget))
            client_earnings[client_id]['jobs_count'] += 1
        
        # Convert to list and sort
        result = []
        for client_id, data in client_earnings.items():
            result.append({
                'client_id': client_id,
                'client_name': data['client'].user.get_full_name() or data['client'].user.username,
                'earnings': str(data['earnings']),
                'jobs_count': data['jobs_count'],
            })
        
        result.sort(key=lambda x: Decimal(x['earnings']), reverse=True)
        
        return result[:limit]
    
    @staticmethod
    def calculate_estimated_tax(
        worker_profile,
        year: int = None,
        tax_rate: Decimal = Decimal('0.25')
    ) -> Dict[str, Any]:
        """
        Calculate estimated tax liability.
        
        Note: This is a rough estimate. Workers should consult a tax professional.
        """
        from jobs.models import JobApplication
        
        if not year:
            year = timezone.now().year
        
        # Get earnings for the year
        year_start = datetime(year, 1, 1).date()
        year_end = datetime(year, 12, 31).date()
        
        jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
            job_request__status='completed',
            created_at__date__gte=year_start,
            created_at__date__lte=year_end,
        ).select_related('job_request')
        
        total_earnings = Decimal('0.00')
        for app in jobs:
            if hasattr(app.job_request, 'budget') and app.job_request.budget:
                total_earnings += Decimal(str(app.job_request.budget))
        
        estimated_tax = total_earnings * tax_rate
        
        # Quarterly estimates
        quarterly_tax = estimated_tax / 4
        
        return {
            'year': year,
            'total_earnings': str(total_earnings),
            'tax_rate': str(tax_rate),
            'estimated_tax': str(estimated_tax.quantize(Decimal('0.01'))),
            'quarterly_estimate': str(quarterly_tax.quantize(Decimal('0.01'))),
            'disclaimer': 'This is an estimate only. Consult a tax professional for accurate calculations.',
        }
    
    @staticmethod
    def get_payment_history(
        worker_profile,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get payment history for a worker.
        """
        from jobs.models import JobApplication
        
        # Get completed jobs
        jobs = JobApplication.objects.filter(
            worker=worker_profile,
            status='accepted',
            job_request__status='completed',
        ).select_related(
            'job_request__client__user'
        ).order_by('-created_at')[:limit]
        
        history = []
        for app in jobs:
            job = app.job_request
            history.append({
                'id': app.id,
                'job_id': job.id,
                'job_title': job.title,
                'client_name': job.client.user.get_full_name() or job.client.user.username,
                'amount': str(job.budget) if hasattr(job, 'budget') and job.budget else '0.00',
                'date': app.created_at.isoformat(),
                'status': 'completed',
            })
        
        return history
