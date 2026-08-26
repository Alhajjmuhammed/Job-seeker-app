import logging
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .notification_models import Notification, NotificationPreference, PushToken
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger('api')

# Which NotificationPreference field gates email for a given notification_type.
# Types with no entry here (system_alert, document_verified) always send -
# they're operational alerts, not spam-risk content.
NOTIFICATION_TYPE_TO_EMAIL_PREF = {
    'job_assigned': 'email_job_assignments',
    'job_accepted': 'email_job_assignments',  # closest existing category
    'job_rejected': 'email_job_assignments',  # closest existing category
    'job_application': 'email_job_applications',
    'job_completed': 'email_job_assignments',  # closest existing category
    'message_received': 'email_messages',
    'payment_received': 'email_payments',
    'review_received': 'email_reviews',
    'promotion': 'email_promotions',
}


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
        """Create a new notification and broadcast via WebSocket"""
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
        
        notification = Notification.objects.create(**notification_data)

        # Broadcast via WebSocket
        NotificationService._broadcast_notification(notification)

        # Email (respects the recipient's per-category preference)
        NotificationService._email_notification(notification)

        return notification

    @staticmethod
    def _email_notification(notification):
        """
        Send an email for this notification, if the recipient hasn't opted
        out of emails for this category. Never raises - an email failure
        (or no SMTP password configured yet) must never break notification
        creation or whatever request triggered it, same defensive pattern
        _broadcast_notification already uses below.
        """
        try:
            recipient = notification.recipient
            if not recipient.email:
                return

            pref_field = NOTIFICATION_TYPE_TO_EMAIL_PREF.get(notification.notification_type)
            if pref_field:
                prefs, _ = NotificationPreference.objects.get_or_create(user=recipient)
                if not getattr(prefs, pref_field):
                    return

            html_message = render_to_string('emails/generic_notification.html', {
                'title': notification.title,
                'message': notification.message,
            })

            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to email notification {notification.id} to {notification.recipient_id}: {e}")

    @staticmethod
    def _broadcast_notification(notification):
        """Broadcast notification via WebSocket to connected clients"""
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'user_{notification.recipient.id}_notifications',
                    {
                        'type': 'notification_message',
                        'data': {
                            'id': notification.id,
                            'title': notification.title,
                            'message': notification.message,
                            'notification_type': notification.notification_type,
                            'is_read': notification.is_read,
                            'created_at': notification.created_at.isoformat(),
                            'extra_data': notification.extra_data,
                        },
                    }
                )
        except Exception as e:
            # Log error but don't fail the notification creation
            import logging
            logging.error(f"Failed to broadcast notification via WebSocket: {e}")
    
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
        # Notify all admins - routed through create_notification (not
        # bulk_create) so each admin also gets the websocket broadcast and
        # email, same as every other notification type.
        admins = User.objects.filter(is_staff=True)
        notifications = []
        for admin in admins:
            notifications.append(
                NotificationService.create_notification(
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
        return notifications
    
    @staticmethod
    def notify_service_completed(service_request):
        """Notify client that service is completed"""
        # Handle multiple workers system
        worker_name = "the assigned worker(s)"
        total_hours = str(service_request.total_hours_worked)
        total_amount = str(service_request.total_amount)
        
        # Get worker info from assignments (new system)
        assignments = service_request.assignments.filter(status='completed')
        if assignments.exists():
            if assignments.count() == 1:
                worker_name = assignments.first().worker.user.get_full_name()
            else:
                worker_name = f"{assignments.count()} workers"
        # Fallback to legacy assigned_worker if exists
        elif service_request.assigned_worker:
            worker_name = service_request.assigned_worker.user.get_full_name()
        
        return NotificationService.create_notification(
            recipient=service_request.client,
            title="Service Completed! ✨",
            message=f"Your service request '{service_request.title}' has been completed by {worker_name}",
            notification_type='job_completed',
            content_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'worker': worker_name,
                'total_hours': total_hours,
                'total_amount': total_amount
            }
        )
    
    @staticmethod
    def notify_service_cancelled(service_request):
        """Notify every worker whose assignment was just cancelled."""
        # assigned_worker is the LEGACY single-worker field and is never
        # populated by the real multi-worker assignment flow - reading it
        # here always silently no-op'd, so no worker was ever notified of
        # a cancellation. ServiceRequest.cancel() calls this right after
        # flipping each active assignment to 'cancelled', so that status is
        # exactly the set of workers actually affected by this cancellation
        # (a previously rejected/completed assignment keeps its own status
        # and is correctly left out).
        notifications = []
        for assignment in service_request.assignments.filter(status='cancelled').select_related('worker__user'):
            notifications.append(NotificationService.create_notification(
                recipient=assignment.worker.user,
                title="Service Cancelled",
                message=f"Service request '{service_request.title}' was cancelled by the client",
                notification_type='system_alert',
                content_object=service_request,
                extra_data={
                    'service_request_id': service_request.id,
                    'assignment_id': assignment.id,
                    'status': 'cancelled'
                }
            ))
        return notifications

    @staticmethod
    def notify_admin_new_service_request(service_request):
        """Notify admin about new service request from client"""
        # Notify all admins - routed through create_notification (not
        # bulk_create) so each admin also gets the websocket broadcast and
        # email, same as every other notification type.
        admins = User.objects.filter(is_staff=True)
        notifications = []
        for admin in admins:
            notifications.append(
                NotificationService.create_notification(
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
        return notifications