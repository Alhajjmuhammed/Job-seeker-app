# URLs for document verification
from django.urls import path
from . import document_verification

urlpatterns = [
    # API endpoints
    path('api/admin/documents/pending/', document_verification.pending_documents, name='admin_pending_documents'),
    path('api/admin/documents/verify/<int:verification_id>/', document_verification.verify_document, name='admin_verify_document'),
    path('api/admin/documents/statistics/', document_verification.verification_statistics, name='admin_verification_statistics'),
    path('api/admin/workers/<int:worker_id>/documents/', document_verification.worker_documents, name='admin_worker_documents'),
    
    # Web views
    path('admin/documents/', document_verification.document_verification_dashboard, name='document_verification_dashboard'),
    path('admin/documents/pending/', document_verification.pending_documents_view, name='pending_documents_view'),
    path('admin/workers/<int:worker_id>/', document_verification.worker_profile_view, name='worker_profile_view'),
]