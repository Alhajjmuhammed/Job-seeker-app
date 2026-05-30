"""
GDPR API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import json

from .gdpr import GDPRService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_my_data(request):
    """
    Export all data associated with the authenticated user.
    
    GDPR Article 20 - Right to Data Portability.
    
    Query params:
        - format: "json" (default) or "file"
    """
    export_format = request.query_params.get('format', 'json')
    
    # Export data
    data = GDPRService.export_user_data(request.user)
    
    if export_format == 'file':
        # Return as downloadable file
        response = HttpResponse(
            json.dumps(data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="my_data_{request.user.id}.json"'
        return response
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deletion_preview(request):
    """
    Preview what data would be deleted if account is deleted.
    
    GDPR Article 17 - Right to Erasure (preview).
    """
    preview = GDPRService.get_erasure_preview(request.user)
    
    return Response({
        'user_id': request.user.id,
        'email': request.user.email,
        'preview': preview,
        'warning': 'This shows what would be deleted. Use /api/v1/gdpr/delete/ to proceed.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def anonymize_account(request):
    """
    Anonymize account data (soft delete).
    
    Keeps records but removes personally identifiable information.
    
    Request body:
        {
            "confirm": true,
            "reason": "optional reason"
        }
    """
    confirm = request.data.get('confirm', False)
    
    if not confirm:
        return Response({
            'error': 'You must confirm this action by setting confirm=true',
            'preview': GDPRService.get_erasure_preview(request.user),
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = GDPRService.anonymize_user(request.user)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Permanently delete all account data.
    
    GDPR Article 17 - Right to Erasure.
    
    This action is IRREVERSIBLE.
    
    Request body:
        {
            "confirm": true,
            "confirm_email": "user@example.com",
            "reason": "optional reason"
        }
    """
    confirm = request.data.get('confirm', False)
    confirm_email = request.data.get('confirm_email', '')
    
    if not confirm:
        return Response({
            'error': 'You must confirm this action by setting confirm=true',
            'preview': GDPRService.get_erasure_preview(request.user),
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if confirm_email != request.user.email:
        return Response({
            'error': 'Email confirmation does not match your account email',
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Log the deletion request
    import logging
    logger = logging.getLogger('security')
    logger.info(
        f"Account deletion requested for user {request.user.id} ({request.user.email})"
    )
    
    result = GDPRService.delete_user_data(request.user, confirm=True)
    
    return Response(result)


@api_view(['GET'])
def data_retention_policy(request):
    """
    Get information about data retention policies.
    
    Public endpoint - no authentication required.
    """
    retention_info = GDPRService.get_data_retention_info()
    
    return Response({
        'retention_policies': retention_info,
        'contact': 'privacy@workerconnect.com',
        'dpo': 'Data Protection Officer contact available upon request',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def data_correction_request(request):
    """
    Request correction of personal data.
    
    GDPR Article 16 - Right to Rectification.
    
    Request body:
        {
            "field": "first_name",
            "current_value": "John",
            "corrected_value": "Jonathan",
            "reason": "Legal name change"
        }
    """
    field = request.data.get('field')
    current_value = request.data.get('current_value')
    corrected_value = request.data.get('corrected_value')
    reason = request.data.get('reason', '')
    
    if not all([field, corrected_value]):
        return Response({
            'error': 'field and corrected_value are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # For immediate updates, handle simple fields directly
    immediate_fields = ['first_name', 'last_name']
    
    if field in immediate_fields:
        setattr(request.user, field, corrected_value)
        request.user.save()
        
        return Response({
            'success': True,
            'field': field,
            'updated_value': corrected_value,
            'message': 'Data updated successfully'
        })
    
    # For other fields, log the request for manual review
    # In production, this would create a support ticket
    import logging
    logger = logging.getLogger('gdpr')
    logger.info(
        f"Data correction request from user {request.user.id}: "
        f"field={field}, reason={reason}"
    )
    
    return Response({
        'success': True,
        'message': 'Your correction request has been logged and will be reviewed.',
        'reference': f"GDPR-{request.user.id}-{field}",
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consent_status(request):
    """
    Get current consent status for the user.
    """
    # In production, this would check actual consent records
    return Response({
        'user_id': request.user.id,
        'consents': {
            'essential_cookies': {
                'status': 'granted',
                'required': True,
                'can_withdraw': False,
            },
            'marketing_emails': {
                'status': 'unknown',
                'required': False,
                'can_withdraw': True,
            },
            'analytics': {
                'status': 'unknown',
                'required': False,
                'can_withdraw': True,
            },
            'data_processing': {
                'status': 'granted',  # Required for service
                'required': True,
                'can_withdraw': False,
                'note': 'Withdrawing requires account deletion',
            },
        }
    })
