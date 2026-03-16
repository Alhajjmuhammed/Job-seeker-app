"""
Notification Helper Functions
Provides easy-to-use functions for creating notifications throughout the application.
"""

from django.contrib.contenttypes.models import ContentType
from .notification_models import Notification
from .notification_service import NotificationService


def create_notification(user, title, message, notification_type, related_object=None, extra_data=None):
    """
    Create a notification for a user.
    
    Args:
        user: User instance who will receive the notification
        title: Notification title (max 200 chars)
        message: Notification message body
        notification_type: One of the NOTIFICATION_TYPES choices
        related_object: Optional related model instance
        extra_data: Optional dict with additional data
    
    Returns:
        Notification instance
    """
    notification = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        content_object=related_object,
        extra_data=extra_data or {}
    )
    
    return notification


def notify_service_request_created(service_request):
    """Notify when a new service request is created."""
    # Notify all workers who match the category
    from workers.models import WorkerProfile
    
    workers = WorkerProfile.objects.filter(
        categories=service_request.category,
        is_available=True,
        is_profile_complete=True
    )
    
    for worker_profile in workers:
        create_notification(
            user=worker_profile.user,
            title=f"New {service_request.category.name} Job Available",
            message=f"A new service request has been posted: {service_request.title}",
            notification_type='job_application',
            related_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'category': service_request.category.name,
                'price': str(service_request.price),
                'location': service_request.location or service_request.city
            }
        )


def notify_application_submitted(application):
    """Notify client when a worker applies to their service request."""
    create_notification(
        user=application.service_request.client,
        title="New Application Received",
        message=f"{application.worker.user.get_full_name()} has applied to your service request: {application.service_request.title}",
        notification_type='job_application',
        related_object=application,
        extra_data={
            'application_id': application.id,
            'worker_name': application.worker.user.get_full_name(),
            'service_request_id': application.service_request.id
        }
    )


def notify_application_accepted(application):
    """Notify worker when their application is accepted."""
    create_notification(
        user=application.worker.user,
        title="Application Accepted! 🎉",
        message=f"Your application for '{application.service_request.title}' has been accepted!",
        notification_type='job_assigned',
        related_object=application,
        extra_data={
            'application_id': application.id,
            'service_request_id': application.service_request.id,
            'client_name': application.service_request.client.get_full_name()
        }
    )


def notify_application_rejected(application):
    """Notify worker when their application is rejected."""
    create_notification(
        user=application.worker.user,
        title="Application Update",
        message=f"Your application for '{application.service_request.title}' was not selected this time.",
        notification_type='job_application',
        related_object=application,
        extra_data={
            'application_id': application.id,
            'service_request_id': application.service_request.id
        }
    )


def notify_worker_assigned(service_request, worker):
    """Notify worker when assigned to a service request."""
    create_notification(
        user=worker.user,
        title="New Job Assignment",
        message=f"You have been assigned to: {service_request.title}",
        notification_type='job_assigned',
        related_object=service_request,
        extra_data={
            'service_request_id': service_request.id,
            'client_name': service_request.client.get_full_name(),
            'price': str(service_request.price)
        }
    )


def notify_service_request_status_change(service_request, old_status, new_status):
    """Notify relevant parties when service request status changes."""
    
    # Notify client
    create_notification(
        user=service_request.client,
        title="Service Request Update",
        message=f"Your request '{service_request.title}' status changed from {old_status} to {new_status}",
        notification_type='job_completed' if new_status == 'completed' else 'account_update',
        related_object=service_request,
        extra_data={
            'service_request_id': service_request.id,
            'old_status': old_status,
            'new_status': new_status
        }
    )
    
    # Notify assigned worker if exists
    if service_request.assigned_worker:
        create_notification(
            user=service_request.assigned_worker.user,
            title="Job Status Update",
            message=f"Job '{service_request.title}' status changed to {new_status}",
            notification_type='job_completed' if new_status == 'completed' else 'account_update',
            related_object=service_request,
            extra_data={
                'service_request_id': service_request.id,
                'old_status': old_status,
                'new_status': new_status
            }
        )


def notify_job_completed(service_request):
    """Notify client when worker marks job as completed."""
    create_notification(
        user=service_request.client,
        title="Job Completed",
        message=f"{service_request.assigned_worker.user.get_full_name()} has marked '{service_request.title}' as completed. Please review and confirm.",
        notification_type='job_completed',
        related_object=service_request,
        extra_data={
            'service_request_id': service_request.id,
            'worker_name': service_request.assigned_worker.user.get_full_name()
        }
    )


def notify_payment_received(service_request, amount):
    """Notify worker when payment is received."""
    create_notification(
        user=service_request.assigned_worker.user,
        title="Payment Received 💰",
        message=f"You have received payment of TSh {amount:,.0f} for '{service_request.title}'",
        notification_type='payment_received',
        related_object=service_request,
        extra_data={
            'service_request_id': service_request.id,
            'amount': str(amount),
            'client_name': service_request.client.get_full_name()
        }
    )


def notify_review_received(review, reviewed_user):
    """Notify user when they receive a review."""
    reviewer_name = review.reviewer.get_full_name() if hasattr(review, 'reviewer') else "A client"
    
    create_notification(
        user=reviewed_user,
        title="New Review Received ⭐",
        message=f"{reviewer_name} has left a review for you: {review.rating}/5 stars",
        notification_type='review_received',
        related_object=review,
        extra_data={
            'review_id': review.id,
            'rating': review.rating,
            'reviewer_name': reviewer_name
        }
    )


def notify_message_received(conversation, sender, recipient, message_preview):
    """Notify user when they receive a new message."""
    create_notification(
        user=recipient,
        title=f"New message from {sender.get_full_name()}",
        message=message_preview[:100] + "..." if len(message_preview) > 100 else message_preview,
        notification_type='message_received',
        related_object=conversation,
        extra_data={
            'conversation_id': conversation.id,
            'sender_id': sender.id,
            'sender_name': sender.get_full_name()
        }
    )


def notify_document_verified(worker, document_type):
    """Notify worker when their document is verified."""
    create_notification(
        user=worker.user,
        title="Document Verified ✅",
        message=f"Your {document_type} has been verified successfully.",
        notification_type='document_verified',
        related_object=worker,
        extra_data={
            'document_type': document_type
        }
    )


def notify_account_update(user, update_message):
    """Notify user about account-related updates."""
    create_notification(
        user=user,
        title="Account Update",
        message=update_message,
        notification_type='account_update',
        extra_data={}
    )


def notify_system_alert(user, alert_title, alert_message):
    """Send a system-wide alert to a user."""
    create_notification(
        user=user,
        title=alert_title,
        message=alert_message,
        notification_type='system_alert',
        extra_data={}
    )


def notify_promotion(user, promotion_title, promotion_message):
    """Send a promotional notification to a user."""
    create_notification(
        user=user,
        title=promotion_title,
        message=promotion_message,
        notification_type='promotion',
        extra_data={}
    )


# Bulk notification functions
def broadcast_notification(users, title, message, notification_type, extra_data=None):
    """
    Send the same notification to multiple users.
    
    Args:
        users: QuerySet or list of User instances
        title: Notification title
        message: Notification message
        notification_type: Notification type
        extra_data: Optional extra data dict
    """
    notifications = []
    for user in users:
        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            extra_data=extra_data or {}
        )
        notifications.append(notification)
    
    return notifications
