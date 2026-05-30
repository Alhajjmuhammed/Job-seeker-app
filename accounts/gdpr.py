"""
GDPR compliance utilities for Worker Connect.

Provides data export and deletion functionality per GDPR requirements.
"""

import json
from datetime import datetime
from django.core.serializers import serialize
from django.http import JsonResponse
from typing import Dict, Any, List


class GDPRService:
    """
    Service for GDPR compliance operations.
    """
    
    @staticmethod
    def export_user_data(user) -> Dict[str, Any]:
        """
        Export all data associated with a user.
        
        Returns a dictionary containing all user-related data.
        Per GDPR Article 20 (Right to Data Portability).
        """
        data = {
            'export_info': {
                'exported_at': datetime.now().isoformat(),
                'user_id': user.id,
                'format_version': '1.0',
            },
            'account_info': {},
            'profile_info': {},
            'jobs': [],
            'applications': [],
            'messages': [],
            'activity_log': [],
        }
        
        # Account information
        data['account_info'] = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active,
        }
        
        # Worker profile
        if hasattr(user, 'worker_profile') and user.worker_profile:
            profile = user.worker_profile
            data['profile_info']['worker'] = {
                'id': profile.id,
                'bio': profile.bio if hasattr(profile, 'bio') else '',
                'skills': profile.skills if hasattr(profile, 'skills') else '',
                'hourly_rate': str(profile.hourly_rate) if hasattr(profile, 'hourly_rate') and profile.hourly_rate else None,
                'location': getattr(profile, 'location', ''),
                'is_verified': profile.is_verified,
                'created_at': profile.created_at.isoformat() if hasattr(profile, 'created_at') else None,
            }
            
            # Applications
            from jobs.models import JobApplication
            applications = JobApplication.objects.filter(worker=profile)
            for app in applications:
                data['applications'].append({
                    'id': app.id,
                    'job_title': app.job_request.title,
                    'status': app.status,
                    'cover_letter': app.cover_letter if hasattr(app, 'cover_letter') else '',
                    'applied_at': app.created_at.isoformat() if hasattr(app, 'created_at') else None,
                })
        
        # Client profile
        if hasattr(user, 'client_profile') and user.client_profile:
            profile = user.client_profile
            data['profile_info']['client'] = {
                'id': profile.id,
                'company_name': getattr(profile, 'company_name', ''),
                'location': getattr(profile, 'location', ''),
                'created_at': profile.created_at.isoformat() if hasattr(profile, 'created_at') else None,
            }
            
            # Service requests posted
            from jobs.service_request_models import ServiceRequest
            jobs = ServiceRequest.objects.filter(client=user)
            for job in jobs:
                data['jobs'].append({
                    'id': job.id,
                    'title': job.title,
                    'description': job.description,
                    'status': job.status,
                    'total_price': str(job.total_price) if job.total_price else None,
                    'location': getattr(job, 'location', ''),
                    'created_at': job.created_at.isoformat(),
                })
        
        # Messages
        from jobs.models import Message
        sent_messages = Message.objects.filter(sender=user)
        received_messages = Message.objects.filter(recipient=user)
        
        for msg in sent_messages:
            data['messages'].append({
                'id': msg.id,
                'type': 'sent',
                'to': msg.recipient.username if msg.recipient else 'Unknown',
                'content': msg.content if msg.content else msg.message,
                'sent_at': msg.created_at.isoformat() if hasattr(msg, 'created_at') else None,
            })
        
        for msg in received_messages:
            data['messages'].append({
                'id': msg.id,
                'type': 'received',
                'from': msg.sender.username if msg.sender else 'Unknown',
                'content': msg.content if msg.content else msg.message,
                'received_at': msg.created_at.isoformat() if hasattr(msg, 'created_at') else None,
            })
        
        # Notifications
        from worker_connect.notification_models import Notification
        notifications = Notification.objects.filter(recipient=user)
        data['notifications'] = []
        for notif in notifications:
            data['notifications'].append({
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'type': notif.notification_type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
                'read_at': notif.read_at.isoformat() if notif.read_at else None,
            })
        
        # Reviews & Ratings
        data['reviews'] = {
            'given': [],
            'received': []
        }
        try:
            from jobs.review_models import Review
            # Reviews given by user
            given_reviews = Review.objects.filter(reviewer=user)
            for review in given_reviews:
                data['reviews']['given'].append({
                    'id': review.id,
                    'rating': review.rating,
                    'comment': review.comment if hasattr(review, 'comment') else '',
                    'created_at': review.created_at.isoformat() if hasattr(review, 'created_at') else None,
                })
            
            # Reviews received by user (if worker)
            if hasattr(user, 'worker_profile') and user.worker_profile:
                received_reviews = Review.objects.filter(worker=user.worker_profile)
                for review in received_reviews:
                    data['reviews']['received'].append({
                        'id': review.id,
                        'rating': review.rating,
                        'comment': review.comment if hasattr(review, 'comment') else '',
                        'reviewer': review.reviewer.username if review.reviewer else 'Anonymous',
                        'created_at': review.created_at.isoformat() if hasattr(review, 'created_at') else None,
                    })
        except:
            # Review model may not exist yet
            pass
        
        # Payment Information
        data['payments'] = []
        try:
            from jobs.payment_models import Payment
            payments = Payment.objects.filter(user=user)
            for payment in payments:
                data['payments'].append({
                    'id': payment.id,
                    'amount': str(payment.amount) if hasattr(payment, 'amount') else None,
                    'status': payment.status if hasattr(payment, 'status') else '',
                    'method': payment.payment_method if hasattr(payment, 'payment_method') else '',
                    'created_at': payment.created_at.isoformat() if hasattr(payment, 'created_at') else None,
                })
        except:
            # Payment model may not exist or have different structure
            pass
        
        # Location Data
        data['location_history'] = []
        # Location data from service requests
        if hasattr(user, 'client_profile'):
            from jobs.service_request_models import ServiceRequest
            requests_with_location = ServiceRequest.objects.filter(client=user).exclude(location='')
            for req in requests_with_location:
                data['location_history'].append({
                    'type': 'service_request',
                    'location': req.location if hasattr(req, 'location') else '',
                    'city': req.city if hasattr(req, 'city') else '',
                    'timestamp': req.created_at.isoformat(),
                })
        
        # Usage Analytics (anonymized where possible)
        data['usage_analytics'] = {
            'account_created': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'total_logins': 'N/A',  # Would need separate tracking
            'total_jobs_posted': len(data['jobs']),
            'total_applications': len(data['applications']),
            'total_messages_sent': len([m for m in data['messages'] if m['type'] == 'sent']),
            'total_messages_received': len([m for m in data['messages'] if m['type'] == 'received']),
            'total_notifications': len(data['notifications']),
        }
        
        return data
    
    @staticmethod
    def get_erasure_preview(user) -> Dict[str, Any]:
        """
        Preview what data will be deleted.
        
        Returns counts of data that would be affected by deletion.
        Per GDPR Article 17 (Right to Erasure).
        """
        preview = {
            'account': True,
            'profiles': {},
            'jobs_count': 0,
            'applications_count': 0,
            'messages_count': 0,
            'documents_count': 0,
        }
        
        if hasattr(user, 'worker_profile') and user.worker_profile:
            from jobs.models import JobApplication
            preview['profiles']['worker'] = True
            preview['applications_count'] = JobApplication.objects.filter(
                worker=user.worker_profile
            ).count()
        
        if hasattr(user, 'client_profile') and user.client_profile:
            from jobs.service_request_models import ServiceRequest
            preview['profiles']['client'] = True
            preview['jobs_count'] = ServiceRequest.objects.filter(
                client=user
            ).count()
        
        from jobs.models import Message
        preview['messages_count'] = Message.objects.filter(
            sender=user
        ).count() + Message.objects.filter(
            recipient=user
        ).count()
        
        # Notifications
        from worker_connect.notification_models import Notification
        preview['notifications_count'] = Notification.objects.filter(
            recipient=user
        ).count()
        
        # Reviews
        try:
            from jobs.review_models import Review
            preview['reviews_given_count'] = Review.objects.filter(reviewer=user).count()
            if hasattr(user, 'worker_profile') and user.worker_profile:
                preview['reviews_received_count'] = Review.objects.filter(
                    worker=user.worker_profile
                ).count()
        except:
            preview['reviews_given_count'] = 0
            preview['reviews_received_count'] = 0
        
        # Payments
        try:
            from jobs.payment_models import Payment
            preview['payments_count'] = Payment.objects.filter(user=user).count()
        except:
            preview['payments_count'] = 0
        
        return preview
    
    @staticmethod
    def anonymize_user(user) -> Dict[str, Any]:
        """
        Anonymize user data instead of full deletion.
        
        Keeps the record but removes PII.
        Useful for maintaining data integrity while respecting privacy.
        """
        import hashlib
        import secrets
        
        # Generate anonymous identifier
        anon_id = hashlib.sha256(
            f"{user.id}-{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        # Store original email hash for duplicate prevention
        email_hash = hashlib.sha256(user.email.encode()).hexdigest()
        
        # Anonymize account
        user.email = f"deleted_{anon_id}@anonymized.local"
        user.username = f"deleted_{anon_id}"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.is_active = False
        user.save()
        
        # Anonymize worker profile
        if hasattr(user, 'worker_profile') and user.worker_profile:
            profile = user.worker_profile
            if hasattr(profile, 'bio'):
                profile.bio = "[Deleted]"
            if hasattr(profile, 'phone'):
                profile.phone = ""
            if hasattr(profile, 'address'):
                profile.address = ""
            profile.save()
        
        # Anonymize client profile  
        if hasattr(user, 'client_profile') and user.client_profile:
            profile = user.client_profile
            if hasattr(profile, 'company_name'):
                profile.company_name = "[Deleted]"
            if hasattr(profile, 'phone'):
                profile.phone = ""
            profile.save()
        
        # Anonymize messages
        from jobs.models import Message
        Message.objects.filter(sender=user).update(
            content="[Message deleted by user]",
            message="[Message deleted by user]"
        )
        
        # Delete notifications (no need to keep)
        from worker_connect.notification_models import Notification
        Notification.objects.filter(recipient=user).delete()
        
        return {
            'success': True,
            'anonymous_id': anon_id,
            'email_hash': email_hash,  # For support purposes
            'message': 'User data has been anonymized'
        }
    
    @staticmethod
    def delete_user_data(user, confirm: bool = False) -> Dict[str, Any]:
        """
        Permanently delete all user data.
        
        Requires explicit confirmation.
        This is irreversible.
        """
        if not confirm:
            return {
                'success': False,
                'error': 'Deletion must be explicitly confirmed',
                'preview': GDPRService.get_erasure_preview(user),
            }
        
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Delete related data first
                if hasattr(user, 'worker_profile') and user.worker_profile:
                    from jobs.models import JobApplication
                    JobApplication.objects.filter(
                        worker=user.worker_profile
                    ).delete()
                    user.worker_profile.delete()
                
                if hasattr(user, 'client_profile') and user.client_profile:
                    from jobs.service_request_models import ServiceRequest
                    # Delete service requests for this client
                    ServiceRequest.objects.filter(
                        client=user
                    ).delete()
                    user.client_profile.delete()
                
                # Delete messages
                from jobs.models import Message
                Message.objects.filter(sender=user).delete()
                Message.objects.filter(recipient=user).delete()
                
                # Delete notifications
                from worker_connect.notification_models import Notification
                Notification.objects.filter(recipient=user).delete()
                
                # Delete reviews (received reviews kept anonymized for workers)
                try:
                    from jobs.review_models import Review
                    Review.objects.filter(reviewer=user).update(
                        reviewer=None,
                        comment="[Review author deleted account]"
                    )
                except:
                    pass
                
                # Keep payment records for 7 years (legal requirement)
                # Mark as anonymized instead of deleting
                try:
                    from jobs.payment_models import Payment
                    Payment.objects.filter(user=user).update(
                        user=None,  # Null the user relationship
                        # Keep payment records for legal/tax purposes
                    )
                except:
                    pass
                
                # Finally delete user
                user_id = user.id
                user.delete()
                
                return {
                    'success': True,
                    'deleted_user_id': user_id,
                    'message': 'All user data has been permanently deleted'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def get_data_retention_info() -> Dict[str, Any]:
        """
        Get information about data retention policies.
        """
        return {
            'account_data': {
                'retention_period': 'Until account deletion',
                'legal_basis': 'Contract performance',
            },
            'job_data': {
                'retention_period': '3 years after completion',
                'legal_basis': 'Legal obligations (tax records)',
            },
            'messages': {
                'retention_period': '1 year after last activity',
                'legal_basis': 'Legitimate interest (dispute resolution)',
            },
            'payment_data': {
                'retention_period': '7 years',
                'legal_basis': 'Legal obligations (financial records)',
            },
            'analytics_data': {
                'retention_period': '2 years',
                'legal_basis': 'Legitimate interest (service improvement)',
                'note': 'Anonymized after collection',
            },
        }
