"""
Earnings tracking system for Worker Connect.

Tracks worker earnings, payments, and financial reports.

Earnings are computed from ServiceRequestAssignment.worker_payment - the
current admin-mediated assignment system - not the legacy JobApplication/
JobRequest.budget job board, which real workers in this system don't use.
"""

from django.db.models import Sum
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
        from jobs.service_request_models import ServiceRequestAssignment

        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date()
        if not end_date:
            end_date = timezone.now().date()

        # Completed assignments in period (paid work)
        completed = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status='completed',
            work_completed_at__date__gte=start_date,
            work_completed_at__date__lte=end_date,
        )
        total_jobs = completed.count()
        total_earnings = completed.aggregate(total=Sum('worker_payment'))['total'] or Decimal('0.00')

        # Pending payments (accepted/in-progress, not yet completed)
        pending = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status__in=['accepted', 'in_progress'],
        )
        pending_count = pending.count()
        pending_earnings = pending.aggregate(total=Sum('worker_payment'))['total'] or Decimal('0.00')

        avg_per_job = (total_earnings / total_jobs).quantize(Decimal('0.01')) if total_jobs > 0 else Decimal('0.00')

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'earnings': {
                'total': str(total_earnings),
                'pending': str(pending_earnings),
                'average_per_job': str(avg_per_job),
            },
            'jobs': {
                'completed': total_jobs,
                'pending': pending_count,
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
        from jobs.service_request_models import ServiceRequestAssignment

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
                period_end = (now - timedelta(days=30 * i)).date()
                period_start = period_end - timedelta(days=29)
                label = period_end.strftime('%Y-%m')

            assignments = ServiceRequestAssignment.objects.filter(
                worker=worker_profile,
                status='completed',
                work_completed_at__date__gte=period_start,
                work_completed_at__date__lte=period_end,
            )
            earnings = assignments.aggregate(total=Sum('worker_payment'))['total'] or Decimal('0.00')

            breakdown.append({
                'period': label,
                'start_date': period_start.isoformat(),
                'end_date': period_end.isoformat(),
                'earnings': str(earnings),
                'jobs_count': assignments.count(),
            })

        # Reverse to show oldest first
        breakdown.reverse()

        return breakdown

    @staticmethod
    def get_earnings_by_category(worker_profile) -> List[Dict[str, Any]]:
        """
        Get earnings breakdown by job category/type.
        """
        from jobs.service_request_models import ServiceRequestAssignment

        assignments = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status='completed',
        ).select_related('service_request__category')

        category_earnings = {}

        for assignment in assignments:
            category_obj = assignment.service_request.category
            category = category_obj.name if category_obj else 'Other'

            if category not in category_earnings:
                category_earnings[category] = {
                    'earnings': Decimal('0.00'),
                    'count': 0,
                }

            category_earnings[category]['earnings'] += assignment.worker_payment
            category_earnings[category]['count'] += 1

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

        result.sort(key=lambda x: Decimal(x['earnings']), reverse=True)

        return result

    @staticmethod
    def get_top_clients(worker_profile, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top clients by earnings.
        """
        from jobs.service_request_models import ServiceRequestAssignment

        assignments = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status='completed',
        ).select_related('service_request__client')

        client_earnings = {}

        for assignment in assignments:
            client = assignment.service_request.client
            client_id = client.id

            if client_id not in client_earnings:
                client_earnings[client_id] = {
                    'client': client,
                    'earnings': Decimal('0.00'),
                    'jobs_count': 0,
                }

            client_earnings[client_id]['earnings'] += assignment.worker_payment
            client_earnings[client_id]['jobs_count'] += 1

        result = []
        for client_id, data in client_earnings.items():
            result.append({
                'client_id': client_id,
                'client_name': data['client'].get_full_name() or data['client'].username,
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
        from jobs.service_request_models import ServiceRequestAssignment

        if not year:
            year = timezone.now().year

        year_start = datetime(year, 1, 1).date()
        year_end = datetime(year, 12, 31).date()

        assignments = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status='completed',
            work_completed_at__date__gte=year_start,
            work_completed_at__date__lte=year_end,
        )
        total_earnings = assignments.aggregate(total=Sum('worker_payment'))['total'] or Decimal('0.00')

        estimated_tax = total_earnings * tax_rate
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
        from jobs.service_request_models import ServiceRequestAssignment

        assignments = ServiceRequestAssignment.objects.filter(
            worker=worker_profile,
            status='completed',
        ).select_related(
            'service_request__client'
        ).order_by('-work_completed_at')[:limit]

        history = []
        for assignment in assignments:
            service_request = assignment.service_request
            client = service_request.client
            history.append({
                'id': assignment.id,
                'job_id': service_request.id,
                'job_title': service_request.title,
                'client_name': client.get_full_name() or client.username,
                'amount': str(assignment.worker_payment),
                'date': (assignment.work_completed_at or assignment.assigned_at).isoformat(),
                'status': 'completed',
            })

        return history
