"""
Report/Flag system for Worker Connect.

Allows users to report inappropriate content, users, or behavior.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class ReportType:
    """Report type constants."""
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    INAPPROPRIATE_CONTENT = 'inappropriate_content'
    FRAUD = 'fraud'
    FAKE_PROFILE = 'fake_profile'
    SAFETY_CONCERN = 'safety_concern'
    OTHER = 'other'
    
    CHOICES = [
        (SPAM, 'Spam'),
        (HARASSMENT, 'Harassment'),
        (INAPPROPRIATE_CONTENT, 'Inappropriate Content'),
        (FRAUD, 'Fraud or Scam'),
        (FAKE_PROFILE, 'Fake Profile'),
        (SAFETY_CONCERN, 'Safety Concern'),
        (OTHER, 'Other'),
    ]


class ReportStatus:
    """Report status constants."""
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    RESOLVED = 'resolved'
    DISMISSED = 'dismissed'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (UNDER_REVIEW, 'Under Review'),
        (RESOLVED, 'Resolved'),
        (DISMISSED, 'Dismissed'),
    ]


class ContentType:
    """Content types that can be reported."""
    USER = 'user'
    JOB = 'job'
    MESSAGE = 'message'
    REVIEW = 'review'
    
    CHOICES = [
        (USER, 'User'),
        (JOB, 'Job Posting'),
        (MESSAGE, 'Message'),
        (REVIEW, 'Review'),
    ]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_report(request):
    """
    Submit a report for inappropriate content or user.
    
    Body:
        - content_type: Type of content being reported (user, job, message, review)
        - content_id: ID of the content being reported
        - report_type: Type of report (spam, harassment, etc.)
        - description: Detailed description of the issue
    """
    from jobs.models import Report
    
    user = request.user
    content_type = request.data.get('content_type')
    content_id = request.data.get('content_id')
    report_type = request.data.get('report_type')
    description = request.data.get('description', '').strip()
    
    # Validation
    if not all([content_type, content_id, report_type]):
        return Response(
            {'error': 'content_type, content_id, and report_type are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if content_type not in dict(ContentType.CHOICES):
        return Response(
            {'error': f'Invalid content_type. Must be one of: {", ".join(dict(ContentType.CHOICES).keys())}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if report_type not in dict(ReportType.CHOICES):
        return Response(
            {'error': f'Invalid report_type. Must be one of: {", ".join(dict(ReportType.CHOICES).keys())}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(description) > 2000:
        return Response(
            {'error': 'Description too long (max 2000 characters)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user already reported this content
    existing = Report.objects.filter(
        reporter=user,
        content_type=content_type,
        content_id=content_id,
        status__in=[ReportStatus.PENDING, ReportStatus.UNDER_REVIEW]
    ).exists()
    
    if existing:
        return Response(
            {'error': 'You have already reported this content'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify content exists
    reported_user = None
    if content_type == ContentType.USER:
        try:
            reported_user = User.objects.get(id=content_id)
            if reported_user == user:
                return Response(
                    {'error': 'You cannot report yourself'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    elif content_type == ContentType.JOB:
        from jobs.models import JobRequest
        try:
            job = JobRequest.objects.get(id=content_id)
            reported_user = job.client.user
        except JobRequest.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Create report
    report = Report.objects.create(
        reporter=user,
        reported_user=reported_user,
        content_type=content_type,
        content_id=content_id,
        report_type=report_type,
        description=description,
        status=ReportStatus.PENDING,
    )
    
    logger.info(f"Report {report.id} submitted by user {user.id} for {content_type}:{content_id}")
    
    # Notify admins if high priority
    if report_type in [ReportType.SAFETY_CONCERN, ReportType.FRAUD]:
        try:
            from worker_connect.notifications import notify_admins_urgent_report
            notify_admins_urgent_report(report)
        except Exception:
            pass
    
    return Response({
        'report_id': report.id,
        'message': 'Report submitted successfully. Our team will review it shortly.',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_reports(request):
    """
    List all reports (admin only).
    
    Query params:
        - status: Filter by status
        - report_type: Filter by report type
        - content_type: Filter by content type
        - page: Page number
        - page_size: Items per page
    """
    from jobs.models import Report
    
    status_filter = request.query_params.get('status')
    report_type = request.query_params.get('report_type')
    content_type = request.query_params.get('content_type')
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    
    reports = Report.objects.select_related('reporter', 'reported_user', 'reviewed_by')
    
    if status_filter:
        reports = reports.filter(status=status_filter)
    if report_type:
        reports = reports.filter(report_type=report_type)
    if content_type:
        reports = reports.filter(content_type=content_type)
    
    reports = reports.order_by('-created_at')
    
    total_count = reports.count()
    start = (page - 1) * page_size
    reports = reports[start:start + page_size]
    
    return Response({
        'reports': [
            {
                'id': r.id,
                'reporter': {
                    'id': r.reporter.id,
                    'email': r.reporter.email,
                    'name': f"{r.reporter.first_name} {r.reporter.last_name}",
                },
                'reported_user': {
                    'id': r.reported_user.id,
                    'email': r.reported_user.email,
                    'name': f"{r.reported_user.first_name} {r.reported_user.last_name}",
                } if r.reported_user else None,
                'content_type': r.content_type,
                'content_id': r.content_id,
                'report_type': r.report_type,
                'description': r.description,
                'status': r.status,
                'created_at': r.created_at.isoformat(),
                'reviewed_by': r.reviewed_by.email if r.reviewed_by else None,
                'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in reports
        ],
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def review_report(request, report_id):
    """
    Review and update a report (admin only).
    
    Body:
        - status: New status (resolved, dismissed)
        - action_taken: Description of action taken
        - ban_user: Whether to ban the reported user (optional)
    """
    from jobs.models import Report
    
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_status = request.data.get('status')
    action_taken = request.data.get('action_taken', '')
    ban_user = request.data.get('ban_user', False)
    
    if new_status not in [ReportStatus.RESOLVED, ReportStatus.DISMISSED, ReportStatus.UNDER_REVIEW]:
        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update report
    report.status = new_status
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.action_taken = action_taken
    report.save()
    
    # Ban user if requested
    if ban_user and report.reported_user:
        report.reported_user.is_active = False
        report.reported_user.save()
        logger.warning(f"User {report.reported_user.id} banned due to report {report.id}")
    
    logger.info(f"Report {report.id} reviewed by {request.user.email}: {new_status}")
    
    return Response({
        'message': 'Report updated successfully',
        'status': new_status,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def report_statistics(request):
    """Get report statistics for admin dashboard."""
    from jobs.models import Report
    
    stats = {
        'total': Report.objects.count(),
        'pending': Report.objects.filter(status=ReportStatus.PENDING).count(),
        'under_review': Report.objects.filter(status=ReportStatus.UNDER_REVIEW).count(),
        'resolved': Report.objects.filter(status=ReportStatus.RESOLVED).count(),
        'dismissed': Report.objects.filter(status=ReportStatus.DISMISSED).count(),
    }
    
    # Reports by type
    by_type = Report.objects.values('report_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Reports by content type
    by_content = Report.objects.values('content_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent reports (last 7 days)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_count = Report.objects.filter(created_at__gte=week_ago).count()
    
    return Response({
        'summary': stats,
        'by_type': list(by_type),
        'by_content_type': list(by_content),
        'recent_7_days': recent_count,
    })
