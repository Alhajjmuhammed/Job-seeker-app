"""
Admin analytics API views for Worker Connect dashboard.

Provides statistics and metrics for the admin panel.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Sum, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from jobs.models import JobRequest, JobApplication
from workers.models import WorkerProfile

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_overview(request):
    """
    Get overview statistics for the admin dashboard.
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    
    # User statistics
    total_users = User.objects.count()
    total_workers = User.objects.filter(user_type='worker').count()
    total_clients = User.objects.filter(user_type='client').count()
    new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    new_users_7d = User.objects.filter(date_joined__gte=seven_days_ago).count()
    
    # Job statistics
    total_jobs = JobRequest.objects.count()
    active_jobs = JobRequest.objects.filter(status='open').count()
    completed_jobs = JobRequest.objects.filter(status='completed').count()
    new_jobs_30d = JobRequest.objects.filter(created_at__gte=thirty_days_ago).count()
    
    # Application statistics
    total_applications = JobApplication.objects.count()
    pending_applications = JobApplication.objects.filter(status='pending').count()
    accepted_applications = JobApplication.objects.filter(status='accepted').count()
    
    # Worker statistics
    available_workers = WorkerProfile.objects.filter(is_available=True).count()
    verified_workers = WorkerProfile.objects.filter(is_verified=True).count()
    
    return Response({
        'users': {
            'total': total_users,
            'workers': total_workers,
            'clients': total_clients,
            'new_last_30_days': new_users_30d,
            'new_last_7_days': new_users_7d,
        },
        'jobs': {
            'total': total_jobs,
            'active': active_jobs,
            'completed': completed_jobs,
            'new_last_30_days': new_jobs_30d,
        },
        'applications': {
            'total': total_applications,
            'pending': pending_applications,
            'accepted': accepted_applications,
        },
        'workers': {
            'available': available_workers,
            'verified': verified_workers,
        },
        'generated_at': now.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_growth_chart(request):
    """
    Get user registration data for charts.
    Query params:
        - period: 'daily' (default), 'monthly'
        - days: number of days to look back (default: 30)
    """
    period = request.query_params.get('period', 'daily')
    days = int(request.query_params.get('days', 30))
    
    start_date = timezone.now() - timedelta(days=days)
    
    if period == 'monthly':
        users = User.objects.filter(
            date_joined__gte=start_date
        ).annotate(
            date=TruncMonth('date_joined')
        ).values('date').annotate(
            count=Count('id'),
            workers=Count('id', filter=Q(user_type='worker')),
            clients=Count('id', filter=Q(user_type='client')),
        ).order_by('date')
    else:
        users = User.objects.filter(
            date_joined__gte=start_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id'),
            workers=Count('id', filter=Q(user_type='worker')),
            clients=Count('id', filter=Q(user_type='client')),
        ).order_by('date')
    
    return Response({
        'period': period,
        'data': list(users),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def job_statistics(request):
    """
    Get detailed job statistics.
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Jobs by status
    jobs_by_status = JobRequest.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Jobs by category (if category field exists)
    jobs_by_category = []
    if hasattr(JobRequest, 'category'):
        jobs_by_category = JobRequest.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
    
    # Daily job postings (last 30 days)
    daily_jobs = JobRequest.objects.filter(
        created_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Average applications per job
    avg_applications = JobApplication.objects.values(
        'job_request'
    ).annotate(
        app_count=Count('id')
    ).aggregate(
        avg=Avg('app_count')
    )
    
    return Response({
        'by_status': list(jobs_by_status),
        'by_category': list(jobs_by_category),
        'daily_postings': list(daily_jobs),
        'avg_applications_per_job': avg_applications.get('avg', 0),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def application_statistics(request):
    """
    Get detailed application statistics.
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Applications by status
    by_status = JobApplication.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Daily applications (last 30 days)
    daily_apps = JobApplication.objects.filter(
        applied_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('applied_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Conversion rate (accepted / total)
    total = JobApplication.objects.count()
    accepted = JobApplication.objects.filter(status='accepted').count()
    conversion_rate = (accepted / total * 100) if total > 0 else 0
    
    return Response({
        'by_status': list(by_status),
        'daily_applications': list(daily_apps),
        'conversion_rate': round(conversion_rate, 2),
        'total': total,
        'accepted': accepted,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def worker_statistics(request):
    """
    Get detailed worker statistics.
    """
    # Workers by availability
    by_availability = {
        'available': WorkerProfile.objects.filter(is_available=True).count(),
        'unavailable': WorkerProfile.objects.filter(is_available=False).count(),
    }
    
    # Workers by verification status
    by_verification = {
        'verified': WorkerProfile.objects.filter(is_verified=True).count(),
        'unverified': WorkerProfile.objects.filter(is_verified=False).count(),
    }
    
    # Profile completion stats
    complete_profiles = WorkerProfile.objects.filter(is_profile_complete=True).count()
    incomplete_profiles = WorkerProfile.objects.filter(is_profile_complete=False).count()
    
    # Average rating
    avg_rating = WorkerProfile.objects.aggregate(avg=Avg('rating'))
    
    return Response({
        'by_availability': by_availability,
        'by_verification': by_verification,
        'profile_completion': {
            'complete': complete_profiles,
            'incomplete': incomplete_profiles,
        },
        'average_rating': round(avg_rating.get('avg', 0) or 0, 2),
        'total': WorkerProfile.objects.count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_activity(request):
    """
    Get recent activity feed for the admin dashboard.
    """
    limit = int(request.query_params.get('limit', 20))
    
    # Recent registrations
    recent_users = User.objects.order_by('-date_joined')[:limit].values(
        'id', 'email', 'first_name', 'last_name', 'user_type', 'date_joined'
    )
    
    # Recent jobs
    recent_jobs = JobRequest.objects.order_by('-created_at')[:limit].values(
        'id', 'title', 'status', 'created_at'
    )
    
    # Recent applications
    recent_applications = JobApplication.objects.select_related(
        'worker__user', 'job_request'
    ).order_by('-applied_at')[:limit]
    
    applications_data = [
        {
            'id': app.id,
            'worker_name': f"{app.worker.user.first_name} {app.worker.user.last_name}",
            'job_title': app.job_request.title,
            'status': app.status,
            'applied_at': app.applied_at,
        }
        for app in recent_applications
    ]
    
    return Response({
        'recent_users': list(recent_users),
        'recent_jobs': list(recent_jobs),
        'recent_applications': applications_data,
    })
