from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .notification_models import Notification, NotificationPreference, PushToken
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def create_notification(
        recipient,
        title,
        message,
        notification_type,
        content_object=None,
        extra_data=None
    ):
        """Create a new notification"""
        notification_data = {
            'recipient': recipient,
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'extra_data': extra_data or {}
        }
        
        if content_object:
            notification_data['content_type'] = ContentType.objects.get_for_model(content_object)
            notification_data['object_id'] = content_object.pk
        
        return Notification.objects.create(**notification_data)
    
    @staticmethod
    def notify_job_assigned(job_request, worker):
        """Notify worker about job assignment"""
        return NotificationService.create_notification(
            recipient=worker.user,
            title="New Job Assigned!",
            message=f"You have been assigned to: {job_request.title}",
            notification_type='job_assigned',
            content_object=job_request,
            extra_data={'job_id': job_request.id, 'client': job_request.client.get_full_name()}
        )
    
    @staticmethod
    def notify_job_application(job_request, worker):
        """Notify client about job application"""
        return NotificationService.create_notification(
            recipient=job_request.client,
            title="New Job Application",
            message=f"{worker.get_full_name()} applied for: {job_request.title}",
            notification_type='job_application',
            content_object=job_request,
            extra_data={'job_id': job_request.id, 'worker_id': worker.id}
        )
    
    @staticmethod
    def notify_job_completed(job_request, worker):
        """Notify client about job completion"""
        return NotificationService.create_notification(
            recipient=job_request.client,
            title="Job Completed",
            message=f"{worker.get_full_name()} completed: {job_request.title}",
            notification_type='job_completed',
            content_object=job_request,
            extra_data={'job_id': job_request.id, 'worker_id': worker.id}
        )
    
    @staticmethod
    def notify_message_received(conversation, sender, recipient):
        """Notify about new message"""
        return NotificationService.create_notification(
            recipient=recipient,
            title="New Message",
            message=f"New message from {sender.get_full_name()}",
            notification_type='message_received',
            content_object=conversation,
            extra_data={'sender_id': sender.id, 'conversation_id': conversation.id}
        )
    
    @staticmethod
    def notify_payment_received(payment, recipient):
        """Notify about payment received"""
        return NotificationService.create_notification(
            recipient=recipient,
            title="Payment Received",
            message=f"You received a payment of ${payment.amount}",
            notification_type='payment_received',
            content_object=payment,
            extra_data={'amount': str(payment.amount), 'payment_id': payment.id}
        )
    
    @staticmethod
    def notify_review_received(review, recipient):
        """Notify about new review"""
        stars = "⭐" * review.rating
        return NotificationService.create_notification(
            recipient=recipient,
            title="New Review Received",
            message=f"You received a {review.rating}-star review {stars}",
            notification_type='review_received',
            content_object=review,
            extra_data={'rating': review.rating, 'review_id': review.id}
        )
    
    @staticmethod
    def notify_document_verified(document, worker):
        """Notify worker about document verification"""
        status_msg = "approved" if document.verification_status == 'approved' else "rejected"
        return NotificationService.create_notification(
            recipient=worker.user,
            title="Document Verification Update",
            message=f"Your {document.document_type} has been {status_msg}",
            notification_type='document_verified',
            content_object=document,
            extra_data={'document_type': document.document_type, 'status': document.verification_status}
        )
    
    @staticmethod
    def bulk_notify(recipients, title, message, notification_type, extra_data=None):
        """Send notification to multiple recipients"""
        notifications = []
        for recipient in recipients:
            notifications.append(
                Notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    extra_data=extra_data or {}
                )
            )
        return Notification.objects.bulk_create(notifications)
    
    @staticmethod
    def get_unread_count(user):
        """Get unread notification count for user"""
        return Notification.objects.filter(recipient=user, is_read=False).count()
    
    @staticmethod
    def mark_all_read(user):
        """Mark all notifications as read for user"""
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    # =========================================================================
    # Service Request Notifications (New Admin-Mediated Workflow)
    # =========================================================================
    
    @staticmethod
    def notify_service_assigned(service_request, worker):
        """Notify worker about service assignment by admin"""
        return NotificationService.create_notification(
            recipient=worker.user,
            title="New Service Assigned! 🎯",
            message=f"Admin assigned you to: {service_request.title} in {service_request.city}",
            notification_type='job_assigned',
            content_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'client': service_request.client.get_full_name(),
                'location': service_request.location,
                'urgency': service_request.urgency
            }
        )
    
    @staticmethod
    def notify_service_accepted(service_request):
        """Notify client that worker accepted the assignment"""
        return NotificationService.create_notification(
            recipient=service_request.client,
            title="Worker Accepted Assignment ✅",
            message=f"{service_request.assigned_worker.user.get_full_name()} accepted your service request: {service_request.title}",
            notification_type='job_assigned',
            content_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'worker': service_request.assigned_worker.user.get_full_name(),
                'status': 'accepted'
            }
        )
    
    @staticmethod
    def notify_service_rejected(service_request, reason=''):
        """Notify admin that worker rejected the assignment"""
        # Notify all admins
        admins = User.objects.filter(is_staff=True)
        notifications = []
        for admin in admins:
            notifications.append(
                Notification(
                    recipient=admin,
                    title="Worker Rejected Assignment ⚠️",
                    message=f"Worker rejected service: {service_request.title}. Reason: {reason or 'Not provided'}",
                    notification_type='system_alert',
                    extra_data={
                        'service_request_id': service_request.id,
                        'worker': service_request.assigned_worker.user.get_full_name() if service_request.assigned_worker else None,
                        'reason': reason,
                        'needs_reassignment': True
                    }
                )
            )
        return Notification.objects.bulk_create(notifications)
    
    @staticmethod
    def notify_service_completed(service_request):
        """Notify client that service is completed"""
        return NotificationService.create_notification(
            recipient=service_request.client,
            title="Service Completed! ✨",
            message=f"Your service request '{service_request.title}' has been completed by {service_request.assigned_worker.user.get_full_name()}",
            notification_type='job_completed',
            content_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'worker': service_request.assigned_worker.user.get_full_name(),
                'total_hours': str(service_request.total_hours_worked),
                'total_amount': str(service_request.total_amount)
            }
        )
    
    @staticmethod
    def notify_service_cancelled(service_request):
        """Notify worker that service was cancelled by client"""
        if service_request.assigned_worker:
            return NotificationService.create_notification(
                recipient=service_request.assigned_worker.user,
                title="Service Cancelled",
                message=f"Service request '{service_request.title}' was cancelled by the client",
                notification_type='system_alert',
                content_object=service_request,
                extra_data={
                    'service_request_id': service_request.id,
                    'status': 'cancelled'
                }
            )
    
    @staticmethod
    def notify_admin_new_service_request(service_request):
        """Notify admin about new service request from client"""
        # Notify all admins
        admins = User.objects.filter(is_staff=True)
        notifications = []
        for admin in admins:
            notifications.append(
                Notification(
                    recipient=admin,
                    title="New Service Request 📋",
                    message=f"New {service_request.get_urgency_display()} service request: {service_request.title} in {service_request.city}",
                    notification_type='system_alert',
                    extra_data={
                        'service_request_id': service_request.id,
                        'client': service_request.client.get_full_name(),
                        'category': service_request.category.name if service_request.category else None,
                        'urgency': service_request.urgency,
                        'needs_assignment': True
                    }
                )
            )
        return Notification.objects.bulk_create(notifications)