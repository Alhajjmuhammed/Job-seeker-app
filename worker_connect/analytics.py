"""
Analytics and metrics collection service for Worker Connect.

Provides event tracking, metrics collection, and performance monitoring.
"""

import time
import logging
import json
from typing import Any, Dict, Optional, List
from functools import wraps
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Avg, Sum
from django.utils import timezone

logger = logging.getLogger('analytics')


# =============================================================================
# Event Types
# =============================================================================

class EventType:
    """Event type constants."""
    
    # User events
    USER_REGISTERED = 'user.registered'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_PROFILE_UPDATED = 'user.profile_updated'
    USER_VERIFIED = 'user.verified'
    
    # Job events
    JOB_CREATED = 'job.created'
    JOB_UPDATED = 'job.updated'
    JOB_VIEWED = 'job.viewed'
    JOB_COMPLETED = 'job.completed'
    JOB_CANCELLED = 'job.cancelled'
    JOB_EXPIRED = 'job.expired'
    
    # Application events
    APPLICATION_SUBMITTED = 'application.submitted'
    APPLICATION_ACCEPTED = 'application.accepted'
    APPLICATION_REJECTED = 'application.rejected'
    APPLICATION_WITHDRAWN = 'application.withdrawn'
    
    # Message events
    MESSAGE_SENT = 'message.sent'
    MESSAGE_READ = 'message.read'
    
    # Review events
    REVIEW_SUBMITTED = 'review.submitted'
    REVIEW_UPDATED = 'review.updated'
    
    # Payment events
    INVOICE_CREATED = 'invoice.created'
    INVOICE_SENT = 'invoice.sent'
    PAYMENT_RECEIVED = 'payment.received'
    PAYMENT_FAILED = 'payment.failed'
    
    # Search events
    SEARCH_PERFORMED = 'search.performed'
    SEARCH_RESULT_CLICKED = 'search.result_clicked'
    
    # Error events
    ERROR_OCCURRED = 'error.occurred'
    API_ERROR = 'api.error'


# =============================================================================
# Analytics Service
# =============================================================================

class AnalyticsService:
    """
    Service for tracking analytics events and metrics.
    """
    
    CACHE_PREFIX = 'analytics:'
    METRICS_TTL = 3600  # 1 hour
    
    def __init__(self):
        self.enabled = getattr(settings, 'ANALYTICS_ENABLED', True)
        self.debug = getattr(settings, 'DEBUG', False)
    
    def track(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Track an analytics event.
        
        Args:
            event_type: Type of event (use EventType constants)
            user_id: ID of the user who triggered the event
            properties: Additional event properties
            timestamp: Event timestamp (defaults to now)
        """
        if not self.enabled:
            return
        
        event_data = {
            'type': event_type,
            'user_id': user_id,
            'properties': properties or {},
            'timestamp': (timestamp or timezone.now()).isoformat(),
            'environment': 'development' if self.debug else 'production',
        }
        
        # Log event
        logger.info(f"Analytics event: {event_type}", extra={'event_data': event_data})
        
        # Increment counters
        self._increment_counter(event_type)
        
        # Store recent events for debugging
        if self.debug:
            self._store_recent_event(event_data)
        
        # Send to external analytics service if configured
        self._send_to_external_service(event_data)
    
    def _increment_counter(self, event_type: str) -> None:
        """Increment event counter in cache."""
        try:
            # Daily counter
            today = timezone.now().strftime('%Y-%m-%d')
            daily_key = f"{self.CACHE_PREFIX}count:{event_type}:{today}"
            
            current = cache.get(daily_key, 0)
            cache.set(daily_key, current + 1, timeout=86400 * 7)  # Keep for 7 days
            
            # Hourly counter
            hour = timezone.now().strftime('%Y-%m-%d:%H')
            hourly_key = f"{self.CACHE_PREFIX}count:{event_type}:{hour}"
            
            hourly_current = cache.get(hourly_key, 0)
            cache.set(hourly_key, hourly_current + 1, timeout=86400)  # Keep for 1 day
            
        except Exception as e:
            logger.warning(f"Failed to increment analytics counter: {e}")
    
    def _store_recent_event(self, event_data: Dict) -> None:
        """Store recent events for debugging."""
        try:
            key = f"{self.CACHE_PREFIX}recent_events"
            events = cache.get(key, [])
            events.insert(0, event_data)
            events = events[:100]  # Keep last 100 events
            cache.set(key, events, timeout=3600)
        except Exception as e:
            logger.warning(f"Failed to store recent event: {e}")
    
    def _send_to_external_service(self, event_data: Dict) -> None:
        """
        Send event to external analytics service.
        
        Implement integration with services like:
        - Mixpanel
        - Amplitude
        - Segment
        - Google Analytics
        """
        # Placeholder for external service integration
        pass
    
    def get_event_count(
        self,
        event_type: str,
        date: Optional[str] = None,
    ) -> int:
        """Get event count for a specific type and date."""
        if date is None:
            date = timezone.now().strftime('%Y-%m-%d')
        
        key = f"{self.CACHE_PREFIX}count:{event_type}:{date}"
        return cache.get(key, 0)
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events (debug mode only)."""
        key = f"{self.CACHE_PREFIX}recent_events"
        events = cache.get(key, [])
        return events[:limit]
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for analytics dashboard."""
        today = timezone.now().strftime('%Y-%m-%d')
        
        return {
            'today': {
                'registrations': self.get_event_count(EventType.USER_REGISTERED, today),
                'logins': self.get_event_count(EventType.USER_LOGIN, today),
                'jobs_created': self.get_event_count(EventType.JOB_CREATED, today),
                'applications': self.get_event_count(EventType.APPLICATION_SUBMITTED, today),
                'jobs_completed': self.get_event_count(EventType.JOB_COMPLETED, today),
                'messages_sent': self.get_event_count(EventType.MESSAGE_SENT, today),
                'reviews': self.get_event_count(EventType.REVIEW_SUBMITTED, today),
                'payments': self.get_event_count(EventType.PAYMENT_RECEIVED, today),
                'errors': self.get_event_count(EventType.ERROR_OCCURRED, today),
            },
            'generated_at': timezone.now().isoformat(),
        }


# Global instance
analytics = AnalyticsService()


# =============================================================================
# Performance Metrics
# =============================================================================

class PerformanceMetrics:
    """
    Track and collect performance metrics.
    """
    
    CACHE_PREFIX = 'perf:'
    
    @classmethod
    def track_response_time(
        cls,
        endpoint: str,
        response_time_ms: float,
        status_code: int,
    ) -> None:
        """Track API response time."""
        try:
            today = timezone.now().strftime('%Y-%m-%d')
            key = f"{cls.CACHE_PREFIX}response_times:{endpoint}:{today}"
            
            times = cache.get(key, [])
            times.append({
                'time_ms': response_time_ms,
                'status': status_code,
                'timestamp': timezone.now().isoformat(),
            })
            
            # Keep last 1000 samples per endpoint per day
            times = times[-1000:]
            cache.set(key, times, timeout=86400 * 2)
            
        except Exception as e:
            logger.warning(f"Failed to track response time: {e}")
    
    @classmethod
    def get_response_time_stats(
        cls,
        endpoint: str,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get response time statistics for an endpoint."""
        if date is None:
            date = timezone.now().strftime('%Y-%m-%d')
        
        key = f"{cls.CACHE_PREFIX}response_times:{endpoint}:{date}"
        times = cache.get(key, [])
        
        if not times:
            return {'count': 0}
        
        time_values = [t['time_ms'] for t in times]
        
        return {
            'count': len(times),
            'avg_ms': sum(time_values) / len(time_values),
            'min_ms': min(time_values),
            'max_ms': max(time_values),
            'p95_ms': sorted(time_values)[int(len(time_values) * 0.95)] if len(time_values) >= 20 else None,
        }
    
    @classmethod
    def track_database_query(
        cls,
        query_type: str,
        table: str,
        duration_ms: float,
    ) -> None:
        """Track database query performance."""
        try:
            hour = timezone.now().strftime('%Y-%m-%d:%H')
            key = f"{cls.CACHE_PREFIX}db_queries:{hour}"
            
            queries = cache.get(key, [])
            queries.append({
                'type': query_type,
                'table': table,
                'duration_ms': duration_ms,
            })
            
            queries = queries[-500:]
            cache.set(key, queries, timeout=7200)
            
        except Exception as e:
            logger.warning(f"Failed to track database query: {e}")


# =============================================================================
# Business Metrics
# =============================================================================

class BusinessMetrics:
    """
    Calculate business-level metrics from the database.
    """
    
    @staticmethod
    def get_user_metrics() -> Dict[str, Any]:
        """Get user-related metrics."""
        from django.contrib.auth import get_user_model
        from workers.models import WorkerProfile
        from clients.models import ClientProfile
        
        User = get_user_model()
        
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        return {
            'total_users': User.objects.count(),
            'total_workers': WorkerProfile.objects.count(),
            'total_clients': ClientProfile.objects.count(),
            'new_users_today': User.objects.filter(date_joined__gte=today).count(),
            'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
            'new_users_month': User.objects.filter(date_joined__gte=month_ago).count(),
            'verified_workers': WorkerProfile.objects.filter(is_verified=True).count(),
        }
    
    @staticmethod
    def get_job_metrics() -> Dict[str, Any]:
        """Get job-related metrics."""
        from jobs.models import JobRequest, JobApplication
        
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        jobs = JobRequest.objects.all()
        
        return {
            'total_jobs': jobs.count(),
            'open_jobs': jobs.filter(status='open').count(),
            'in_progress_jobs': jobs.filter(status='in_progress').count(),
            'completed_jobs': jobs.filter(status='completed').count(),
            'jobs_posted_today': jobs.filter(created_at__gte=today).count(),
            'total_applications': JobApplication.objects.count(),
            'pending_applications': JobApplication.objects.filter(status='pending').count(),
            'avg_applications_per_job': JobApplication.objects.values('job').annotate(
                count=Count('id')
            ).aggregate(avg=Avg('count'))['avg'] or 0,
        }
    
    @staticmethod
    def get_financial_metrics() -> Dict[str, Any]:
        """Get financial metrics."""
        from jobs.invoices import Invoice
        
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today.replace(day=1)
        
        invoices = Invoice.objects.all()
        paid_invoices = invoices.filter(status='paid')
        
        return {
            'total_invoices': invoices.count(),
            'paid_invoices': paid_invoices.count(),
            'pending_invoices': invoices.filter(status='sent').count(),
            'overdue_invoices': invoices.filter(status='overdue').count(),
            'total_revenue': paid_invoices.aggregate(total=Sum('total'))['total'] or 0,
            'revenue_this_month': paid_invoices.filter(
                paid_date__gte=month_start
            ).aggregate(total=Sum('total'))['total'] or 0,
        }
    
    @staticmethod
    def get_engagement_metrics() -> Dict[str, Any]:
        """Get user engagement metrics."""
        from jobs.reviews import Review
        from jobs.activity import Activity
        
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        
        return {
            'total_reviews': Review.objects.count(),
            'avg_rating': Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
            'reviews_this_week': Review.objects.filter(created_at__gte=week_ago).count(),
            'activities_today': Activity.objects.filter(timestamp__gte=today).count(),
        }


# =============================================================================
# Decorators
# =============================================================================

def track_event(event_type: str, get_properties=None):
    """
    Decorator to track analytics events.
    
    Usage:
        @track_event(EventType.JOB_CREATED)
        def create_job(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            try:
                # Get user_id from request if available
                user_id = None
                request = args[0] if args else kwargs.get('request')
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user_id = request.user.id
                
                # Get custom properties
                properties = {}
                if get_properties and callable(get_properties):
                    properties = get_properties(*args, **kwargs, result=result)
                
                analytics.track(event_type, user_id=user_id, properties=properties)
                
            except Exception as e:
                logger.warning(f"Failed to track event {event_type}: {e}")
            
            return result
        return wrapper
    return decorator


def measure_performance(endpoint_name: str):
    """
    Decorator to measure endpoint performance.
    
    Usage:
        @measure_performance('jobs.list')
        def list_jobs(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                PerformanceMetrics.track_response_time(
                    endpoint_name,
                    duration_ms,
                    status_code,
                )
            
            return result
        return wrapper
    return decorator


# =============================================================================
# API Views
# =============================================================================

def get_analytics_summary():
    """Get summary of all analytics data."""
    return {
        'events': analytics.get_dashboard_metrics(),
        'users': BusinessMetrics.get_user_metrics(),
        'jobs': BusinessMetrics.get_job_metrics(),
        'financial': BusinessMetrics.get_financial_metrics(),
        'engagement': BusinessMetrics.get_engagement_metrics(),
    }
