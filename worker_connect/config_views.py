from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings

@api_view(['GET'])
@permission_classes([AllowAny])
def terms_of_service(request):
    """Get terms of service content"""
    terms_content = """
    # Terms of Service - Worker Connect
    
    ## 1. Acceptance of Terms
    By using our service, you agree to these terms.
    
    ## 2. Service Description
    Worker Connect is a platform connecting skilled workers with clients.
    
    ## 3. User Responsibilities
    - Provide accurate information
    - Complete jobs as agreed
    - Maintain professional conduct
    
    ## 4. Payment Terms
    - Payments processed through secure channels
    - Platform fee applies to all transactions
    
    ## 5. Dispute Resolution
    Disputes handled through our support system.
    
    Last updated: February 2026
    """
    
    return Response({
        'content': terms_content,
        'last_updated': '2026-02-01',
        'version': '1.0'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def privacy_policy(request):
    """Get privacy policy content"""
    privacy_content = """
    # Privacy Policy - Worker Connect
    
    ## Information We Collect
    - Personal identification information
    - Service usage data
    - Communication records
    
    ## How We Use Information
    - Provide and improve our services
    - Process transactions
    - Send important notifications
    
    ## Information Sharing
    We do not sell personal information to third parties.
    
    ## Data Security
    We implement appropriate security measures.
    
    ## Contact Us
    For privacy concerns, contact us at privacy@workerconnect.com
    
    Last updated: February 2026
    """
    
    return Response({
        'content': privacy_content,
        'last_updated': '2026-02-01',
        'version': '1.0'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def app_version(request):
    """Get current app version info"""
    return Response({
        'version': '1.0.0',
        'build': '100',
        'minimum_supported': '1.0.0',
        'force_update': False,
        'update_message': 'Latest version available'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def contact_info(request):
    """Get contact information"""
    return Response({
        'email': 'support@workerconnect.com',
        'phone': '+1-555-0123',
        'address': '123 Worker Connect St, Tech City, TC 12345',
        'business_hours': 'Monday-Friday 9AM-6PM EST',
        'support_hours': '24/7 for urgent matters'
    })