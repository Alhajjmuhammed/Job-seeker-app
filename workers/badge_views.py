"""
Badge API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from workers.models import WorkerProfile
from .badges import BadgeService, VerificationBadge, WorkerBadge, VerificationTier


@api_view(['GET'])
def get_available_badges(request):
    """
    Get all available badge types.
    """
    badges = VerificationBadge.objects.filter(is_active=True)
    
    result = []
    for badge in badges:
        result.append({
            'type': badge.badge_type,
            'name': badge.name,
            'description': badge.description,
            'requirements': badge.requirements,
            'icon': badge.icon,
            'color': badge.color,
        })
    
    return Response({'badges': result})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_badges(request):
    """
    Get badges for authenticated worker.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    badges = BadgeService.get_worker_badges(worker)
    available = BadgeService.get_available_badges(worker)
    
    return Response({
        'earned_badges': badges,
        'available_badges': available,
    })


@api_view(['GET'])
def get_worker_badges(request, worker_id):
    """
    Get badges for a specific worker.
    """
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    
    # Only show active badges publicly
    badges = WorkerBadge.objects.filter(
        worker=worker,
        status='active'
    ).select_related('badge')
    
    result = []
    for wb in badges:
        if wb.is_valid:
            result.append({
                'name': wb.badge.name,
                'type': wb.badge.badge_type,
                'icon': wb.badge.icon,
                'color': wb.badge.color,
                'issued_at': wb.issued_at.isoformat() if wb.issued_at else None,
            })
    
    return Response({
        'worker_id': worker_id,
        'badges': result,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_badge(request):
    """
    Apply for a verification badge.
    
    Request body:
        {
            "badge_type": "identity_verified",
            "document": <file>  // optional depending on badge type
        }
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    badge_type = request.data.get('badge_type')
    document = request.FILES.get('document')
    
    if not badge_type:
        return Response({
            'error': 'badge_type is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = BadgeService.apply_for_badge(worker, badge_type, document)
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def verify_badge(request, badge_id):
    """
    Admin verifies or rejects a badge application.
    
    Request body:
        {
            "approve": true,
            "notes": "Verification notes",
            "expires_in_days": 365  // optional
        }
    """
    approve = request.data.get('approve', False)
    notes = request.data.get('notes', '')
    expires_in_days = request.data.get('expires_in_days')
    
    result = BadgeService.verify_badge(
        badge_id,
        request.user,
        approve,
        notes,
        expires_in_days
    )
    
    if not result['success']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def pending_badge_applications(request):
    """
    Get pending badge applications for admin review.
    """
    pending = WorkerBadge.objects.filter(
        status='pending'
    ).select_related('worker__user', 'badge').order_by('created_at')
    
    result = []
    for wb in pending:
        result.append({
            'id': wb.id,
            'worker': {
                'id': wb.worker.id,
                'name': wb.worker.user.get_full_name() or wb.worker.user.username,
            },
            'badge': {
                'type': wb.badge.badge_type,
                'name': wb.badge.name,
            },
            'has_document': bool(wb.verification_document),
            'applied_at': wb.created_at.isoformat(),
        })
    
    return Response({
        'count': len(result),
        'applications': result,
    })


@api_view(['GET'])
def get_verification_tiers(request):
    """
    Get all verification tier levels.
    """
    tiers = VerificationTier.objects.filter(is_active=True)
    
    result = []
    for tier in tiers:
        result.append({
            'level': tier.level,
            'name': tier.name,
            'description': tier.description,
            'requirements': {
                'min_reviews': tier.min_reviews,
                'min_rating': float(tier.min_rating),
                'min_completed_jobs': tier.min_completed_jobs,
            },
            'benefits': tier.benefits,
            'commission_rate': float(tier.commission_rate),
            'badge_color': tier.badge_color,
        })
    
    return Response({'tiers': result})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_tier(request):
    """
    Get current verification tier for authenticated worker.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Worker profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    current_level = getattr(worker, 'verification_tier', 1) or 1
    
    try:
        current_tier = VerificationTier.objects.get(level=current_level)
        tier_data = {
            'level': current_tier.level,
            'name': current_tier.name,
            'benefits': current_tier.benefits,
            'commission_rate': float(current_tier.commission_rate),
        }
    except VerificationTier.DoesNotExist:
        tier_data = None
    
    # Get next tier requirements
    next_tier = None
    try:
        next_tier_obj = VerificationTier.objects.filter(
            level__gt=current_level,
            is_active=True
        ).first()
        if next_tier_obj:
            next_tier = {
                'level': next_tier_obj.level,
                'name': next_tier_obj.name,
                'requirements': {
                    'min_reviews': next_tier_obj.min_reviews,
                    'min_rating': float(next_tier_obj.min_rating),
                    'min_completed_jobs': next_tier_obj.min_completed_jobs,
                }
            }
    except:
        pass
    
    return Response({
        'current_tier': tier_data,
        'next_tier': next_tier,
    })
