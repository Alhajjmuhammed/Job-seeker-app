"""
Document verification workflow for Worker Connect.

Handles document upload verification for workers (ID, certifications, etc.)
"""

import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class VerificationStatus:
    """Document verification status constants."""
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED = 'expired'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (UNDER_REVIEW, 'Under Review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (EXPIRED, 'Expired'),
    ]


class DocumentType:
    """Document type constants."""
    GOVERNMENT_ID = 'government_id'
    DRIVERS_LICENSE = 'drivers_license'
    PASSPORT = 'passport'
    CERTIFICATION = 'certification'
    INSURANCE = 'insurance'
    BACKGROUND_CHECK = 'background_check'
    PROOF_OF_ADDRESS = 'proof_of_address'
    OTHER = 'other'
    
    CHOICES = [
        (GOVERNMENT_ID, 'Government ID'),
        (DRIVERS_LICENSE, "Driver's License"),
        (PASSPORT, 'Passport'),
        (CERTIFICATION, 'Professional Certification'),
        (INSURANCE, 'Insurance Document'),
        (BACKGROUND_CHECK, 'Background Check'),
        (PROOF_OF_ADDRESS, 'Proof of Address'),
        (OTHER, 'Other'),
    ]
    
    # Documents that expire
    EXPIRABLE_TYPES = [DRIVERS_LICENSE, PASSPORT, CERTIFICATION, INSURANCE]
    
    # Required documents for worker verification
    REQUIRED_FOR_VERIFICATION = [GOVERNMENT_ID]


class VerificationService:
    """
    Service for managing document verification workflow.
    """
    
    @staticmethod
    def submit_document(
        worker_profile,
        document_type: str,
        file_path: str,
        expiry_date: Optional[str] = None,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Submit a document for verification.
        
        Args:
            worker_profile: WorkerProfile instance
            document_type: Type of document
            file_path: Path to uploaded file
            expiry_date: Optional expiry date (YYYY-MM-DD)
            notes: Optional notes from submitter
            
        Returns:
            Submission result with document ID
        """
        from workers.models import WorkerDocument
        
        # Validate document type
        if document_type not in dict(DocumentType.CHOICES):
            return {
                'success': False,
                'error': 'Invalid document type'
            }
        
        # Check for existing pending/approved document of same type
        existing = WorkerDocument.objects.filter(
            worker=worker_profile,
            document_type=document_type,
            verification_status__in=[VerificationStatus.PENDING, VerificationStatus.UNDER_REVIEW]
        ).first()
        
        if existing:
            return {
                'success': False,
                'error': f'A {document_type} document is already pending review'
            }
        
        # Create document record
        document = WorkerDocument.objects.create(
            worker=worker_profile,
            document_type=document_type,
            file=file_path,
            verification_status=VerificationStatus.PENDING,
            expiry_date=expiry_date,
            notes=notes,
        )
        
        logger.info(f"Document submitted: {document.id} for worker {worker_profile.id}")
        
        return {
            'success': True,
            'document_id': document.id,
            'status': VerificationStatus.PENDING,
            'message': 'Document submitted for review'
        }
    
    @staticmethod
    def review_document(
        document_id: int,
        reviewer,
        approved: bool,
        rejection_reason: str = '',
    ) -> Dict[str, Any]:
        """
        Review a submitted document (admin action).
        
        Args:
            document_id: Document ID to review
            reviewer: User performing the review
            approved: Whether to approve or reject
            rejection_reason: Reason if rejected
            
        Returns:
            Review result
        """
        from workers.models import WorkerDocument
        
        try:
            document = WorkerDocument.objects.get(id=document_id)
        except WorkerDocument.DoesNotExist:
            return {'success': False, 'error': 'Document not found'}
        
        if document.verification_status not in [VerificationStatus.PENDING, VerificationStatus.UNDER_REVIEW]:
            return {'success': False, 'error': 'Document is not pending review'}
        
        # Update document status
        document.verification_status = VerificationStatus.APPROVED if approved else VerificationStatus.REJECTED
        document.reviewed_by = reviewer
        document.reviewed_at = timezone.now()
        document.rejection_reason = rejection_reason if not approved else ''
        document.save()
        
        # Update worker verification status if all required docs approved
        if approved:
            VerificationService._check_worker_verification(document.worker)
        
        logger.info(
            f"Document {document_id} {'approved' if approved else 'rejected'} "
            f"by {reviewer.email}"
        )
        
        return {
            'success': True,
            'status': document.verification_status,
            'message': f'Document {"approved" if approved else "rejected"}'
        }
    
    @staticmethod
    def _check_worker_verification(worker_profile):
        """
        Check if worker has all required documents approved and update verification status.
        """
        from workers.models import WorkerDocument
        
        required_types = DocumentType.REQUIRED_FOR_VERIFICATION
        
        approved_types = WorkerDocument.objects.filter(
            worker=worker_profile,
            verification_status=VerificationStatus.APPROVED,
            document_type__in=required_types
        ).values_list('document_type', flat=True)
        
        all_verified = all(doc_type in approved_types for doc_type in required_types)
        
        if all_verified and not worker_profile.is_verified:
            worker_profile.is_verified = True
            worker_profile.verified_at = timezone.now()
            worker_profile.save()
            logger.info(f"Worker {worker_profile.id} is now verified")
    
    @staticmethod
    def get_verification_status(worker_profile) -> Dict[str, Any]:
        """
        Get comprehensive verification status for a worker.
        
        Returns:
            Dict with verification status, required docs, and submitted docs
        """
        from workers.models import WorkerDocument
        
        documents = WorkerDocument.objects.filter(worker=worker_profile)
        
        # Group by type and get latest of each
        doc_status = {}
        for doc in documents:
            if doc.document_type not in doc_status or doc.created_at > doc_status[doc.document_type]['created_at']:
                doc_status[doc.document_type] = {
                    'id': doc.id,
                    'status': doc.verification_status,
                    'created_at': doc.created_at,
                    'expiry_date': doc.expiry_date,
                }
        
        # Check required documents
        required_status = []
        for doc_type in DocumentType.REQUIRED_FOR_VERIFICATION:
            status = doc_status.get(doc_type, {}).get('status')
            required_status.append({
                'type': doc_type,
                'label': dict(DocumentType.CHOICES).get(doc_type),
                'submitted': doc_type in doc_status,
                'status': status,
                'approved': status == VerificationStatus.APPROVED,
            })
        
        return {
            'is_verified': worker_profile.is_verified,
            'verified_at': worker_profile.verified_at,
            'required_documents': required_status,
            'all_documents': doc_status,
            'pending_count': sum(1 for d in doc_status.values() if d['status'] == VerificationStatus.PENDING),
        }
    
    @staticmethod
    def check_expiring_documents(days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Find documents expiring within specified days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of expiring documents
        """
        from workers.models import WorkerDocument
        
        expiry_threshold = timezone.now().date() + timezone.timedelta(days=days_ahead)
        
        expiring = WorkerDocument.objects.filter(
            verification_status=VerificationStatus.APPROVED,
            document_type__in=DocumentType.EXPIRABLE_TYPES,
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=timezone.now().date(),
        ).select_related('worker__user')
        
        return [
            {
                'document_id': doc.id,
                'worker_id': doc.worker.id,
                'worker_email': doc.worker.user.email,
                'document_type': doc.document_type,
                'expiry_date': doc.expiry_date,
                'days_until_expiry': (doc.expiry_date - timezone.now().date()).days,
            }
            for doc in expiring
        ]
    
    @staticmethod
    def expire_outdated_documents():
        """
        Mark expired documents and update worker verification status.
        Called by scheduled task.
        """
        from workers.models import WorkerDocument
        
        today = timezone.now().date()
        
        # Find and expire documents
        expired_docs = WorkerDocument.objects.filter(
            verification_status=VerificationStatus.APPROVED,
            expiry_date__lt=today,
        )
        
        affected_workers = set()
        for doc in expired_docs:
            doc.verification_status = VerificationStatus.EXPIRED
            doc.save()
            affected_workers.add(doc.worker_id)
            logger.info(f"Document {doc.id} marked as expired")
        
        # Re-check verification status for affected workers
        from workers.models import WorkerProfile
        for worker_id in affected_workers:
            try:
                worker = WorkerProfile.objects.get(id=worker_id)
                # Check if still has all required docs
                VerificationService._check_worker_verification(worker)
                
                # If was verified but now missing required docs, un-verify
                if worker.is_verified:
                    status = VerificationService.get_verification_status(worker)
                    if not all(doc['approved'] for doc in status['required_documents']):
                        worker.is_verified = False
                        worker.save()
                        logger.info(f"Worker {worker.id} verification revoked due to expired documents")
            except Exception as e:
                logger.error(f"Error updating worker {worker_id} verification: {e}")
        
        return len(expired_docs)
