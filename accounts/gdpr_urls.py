"""
URL routes for GDPR compliance.
"""

from django.urls import path
from . import gdpr_views

urlpatterns = [
    # Data export (Right to Portability)
    path('export/', gdpr_views.export_my_data, name='gdpr_export'),
    
    # Deletion (Right to Erasure)
    path('delete/preview/', gdpr_views.deletion_preview, name='gdpr_delete_preview'),
    path('delete/', gdpr_views.delete_account, name='gdpr_delete'),
    path('anonymize/', gdpr_views.anonymize_account, name='gdpr_anonymize'),
    
    # Correction (Right to Rectification)
    path('correct/', gdpr_views.data_correction_request, name='gdpr_correct'),
    
    # Information
    path('retention/', gdpr_views.data_retention_policy, name='gdpr_retention'),
    path('consent/', gdpr_views.consent_status, name='gdpr_consent'),
]
