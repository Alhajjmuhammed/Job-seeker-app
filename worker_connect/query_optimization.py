"""
Database query optimization utilities for Worker Connect.

Provides helpers for efficient database queries using select_related and prefetch_related.
"""

from django.db.models import Prefetch, Count, Avg
from functools import wraps


class QueryOptimizer:
    """
    Collection of optimized query methods for common patterns.
    """
    
    # Job-related optimizations
    @staticmethod
    def get_jobs_with_relations(queryset):
        """
        Optimize job queries with related data.
        """
        return queryset.select_related(
            'client__user',
            'category',
        ).prefetch_related(
            'assigned_workers__user',
            'applications__worker__user',
            'required_skills',
        )
    
    @staticmethod
    def get_job_list(queryset):
        """
        Optimize job list queries (lighter than full relations).
        """
        return queryset.select_related(
            'client__user',
            'category',
        ).only(
            'id', 'title', 'description', 'status', 'budget',
            'location', 'created_at', 'scheduled_date',
            'client__id', 'client__user__first_name', 'client__user__last_name',
            'category__id', 'category__name',
        )
    
    @staticmethod
    def get_job_detail(job_id):
        """
        Get a single job with all related data.
        """
        from jobs.models import JobRequest, JobApplication
        
        return JobRequest.objects.select_related(
            'client__user',
            'category',
        ).prefetch_related(
            Prefetch(
                'applications',
                queryset=JobApplication.objects.select_related('worker__user')
            ),
            'assigned_workers__user',
            'required_skills',
        ).get(id=job_id)
    
    # Worker-related optimizations
    @staticmethod
    def get_workers_with_relations(queryset):
        """
        Optimize worker queries with related data.
        """
        return queryset.select_related(
            'user',
        ).prefetch_related(
            'categories',
            'skills',
            'badges__badge',
        )
    
    @staticmethod
    def get_worker_list(queryset):
        """
        Optimize worker list queries.
        """
        return queryset.select_related(
            'user',
        ).prefetch_related(
            'categories',
        ).only(
            'id', 'hourly_rate', 'rating', 'total_reviews',
            'total_jobs_completed', 'availability_status', 'is_verified',
            'user__id', 'user__first_name', 'user__last_name', 'user__email',
        )
    
    @staticmethod
    def get_worker_detail(worker_id):
        """
        Get a single worker with all related data.
        """
        from workers.models import WorkerProfile
        from workers.badges import WorkerBadge
        from workers.portfolio import PortfolioItem
        
        return WorkerProfile.objects.select_related(
            'user',
        ).prefetch_related(
            'categories',
            'skills',
            Prefetch(
                'badges',
                queryset=WorkerBadge.objects.filter(status='active').select_related('badge')
            ),
            Prefetch(
                'portfolio_items',
                queryset=PortfolioItem.objects.filter(is_public=True)
            ),
        ).get(id=worker_id)
    
    # Application-related optimizations
    @staticmethod
    def get_applications_for_job(job):
        """
        Get applications for a job with worker details.
        """
        from jobs.models import JobApplication
        
        return JobApplication.objects.filter(
            job=job
        ).select_related(
            'worker__user',
        ).prefetch_related(
            'worker__categories',
        ).order_by('-created_at')
    
    @staticmethod
    def get_applications_for_worker(worker):
        """
        Get applications by a worker with job details.
        """
        from jobs.models import JobApplication
        
        return JobApplication.objects.filter(
            worker=worker
        ).select_related(
            'job__client__user',
            'job__category',
        ).order_by('-created_at')
    
    # Review-related optimizations
    @staticmethod
    def get_reviews_for_user(user):
        """
        Get reviews for a user with related data.
        """
        from jobs.reviews import Review
        
        return Review.objects.filter(
            reviewee=user,
            is_visible=True,
        ).select_related(
            'reviewer',
            'job',
        ).order_by('-created_at')
    
    # Invoice-related optimizations
    @staticmethod
    def get_invoices_with_items(queryset):
        """
        Get invoices with line items.
        """
        from jobs.invoices import InvoiceItem
        
        return queryset.select_related(
            'worker__user',
            'client__user',
            'job',
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=InvoiceItem.objects.all()
            ),
        )


def optimize_queryset(optimization_type):
    """
    Decorator to automatically optimize querysets in views.
    
    Usage:
        @optimize_queryset('job_list')
        def list_jobs(request):
            return JobRequest.objects.filter(status='open')
    """
    optimizers = {
        'job_list': QueryOptimizer.get_job_list,
        'jobs_with_relations': QueryOptimizer.get_jobs_with_relations,
        'worker_list': QueryOptimizer.get_worker_list,
        'workers_with_relations': QueryOptimizer.get_workers_with_relations,
        'invoices_with_items': QueryOptimizer.get_invoices_with_items,
    }
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if optimization_type in optimizers:
                return optimizers[optimization_type](result)
            
            return result
        return wrapper
    return decorator


class EagerLoadMixin:
    """
    Mixin for views to add eager loading.
    
    Usage:
        class JobViewSet(EagerLoadMixin, viewsets.ModelViewSet):
            select_related_fields = ['client__user', 'category']
            prefetch_related_fields = ['applications', 'assigned_workers']
    """
    
    select_related_fields = []
    prefetch_related_fields = []
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset


class QueryCountDebugMixin:
    """
    Mixin to debug query counts in development.
    
    Usage:
        class JobViewSet(QueryCountDebugMixin, viewsets.ModelViewSet):
            ...
    """
    
    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings
        from django.db import connection, reset_queries
        
        if settings.DEBUG:
            reset_queries()
        
        response = super().dispatch(request, *args, **kwargs)
        
        if settings.DEBUG:
            query_count = len(connection.queries)
            total_time = sum(float(q['time']) for q in connection.queries)
            
            response['X-Query-Count'] = str(query_count)
            response['X-Query-Time'] = f"{total_time:.3f}s"
            
            if query_count > 10:
                import logging
                logger = logging.getLogger('django.db.backends')
                logger.warning(
                    f"High query count: {query_count} queries for {request.path}"
                )
        
        return response
