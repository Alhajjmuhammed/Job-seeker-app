"""
Push notifications service for Worker Connect mobile app.

Supports Firebase Cloud Messaging (FCM) for mobile push notifications.
"""

import logging
from typing import Optional, List, Dict
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

# Try to import firebase-admin (optional dependency)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.info("firebase-admin not installed. Push notifications disabled.")


class PushNotificationService:
    """
    Service for sending push notifications via Firebase Cloud Messaging.
    """
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK."""
        if cls._initialized or not FIREBASE_AVAILABLE:
            return
        
        try:
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("FIREBASE_CREDENTIALS_PATH not set. Push notifications disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if push notifications are available."""
        return FIREBASE_AVAILABLE and cls._initialized
    
    @classmethod
    def send_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        """
        Send a push notification to a single device.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body text
            data: Optional custom data payload
            image_url: Optional image URL for rich notifications
            
        Returns:
            bool: True if sent successfully
        """
        if not cls.is_available():
            logger.debug("Push notifications not available")
            return False
        
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )
            
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token,
            )
            
            response = messaging.send(message)
            logger.info(f"Notification sent successfully: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"Token unregistered: {token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    @classmethod
    def send_multicast(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        """
        Send push notification to multiple devices.
        
        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body text
            data: Optional custom data payload
            
        Returns:
            Dict with success_count and failure_count
        """
        if not cls.is_available():
            return {'success_count': 0, 'failure_count': len(tokens)}
        
        if not tokens:
            return {'success_count': 0, 'failure_count': 0}
        
        try:
            notification = messaging.Notification(title=title, body=body)
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=tokens,
            )
            
            response = messaging.send_multicast(message)
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
            
        except Exception as e:
            logger.error(f"Failed to send multicast notification: {e}")
            return {'success_count': 0, 'failure_count': len(tokens)}
    
    @classmethod
    def send_to_topic(
        cls,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send notification to all devices subscribed to a topic.
        
        Args:
            topic: FCM topic name (e.g., 'new_jobs', 'workers_nearby')
            title: Notification title
            body: Notification body text
            data: Optional custom data payload
            
        Returns:
            bool: True if sent successfully
        """
        if not cls.is_available():
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
            )
            
            response = messaging.send(message)
            logger.info(f"Topic notification sent: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send topic notification: {e}")
            return False
    
    @classmethod
    def subscribe_to_topic(cls, tokens: List[str], topic: str) -> bool:
        """Subscribe devices to a topic."""
        if not cls.is_available():
            return False
        
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(f"Subscribed {response.success_count} tokens to {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to topic: {e}")
            return False
    
    @classmethod
    def unsubscribe_from_topic(cls, tokens: List[str], topic: str) -> bool:
        """Unsubscribe devices from a topic."""
        if not cls.is_available():
            return False
        
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(f"Unsubscribed {response.success_count} tokens from {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic: {e}")
            return False


# Notification templates for common events
class NotificationTemplates:
    """Pre-defined notification templates for common app events."""
    
    @staticmethod
    def job_application_received(job_title: str, applicant_name: str) -> Dict[str, str]:
        """Notification for clients when they receive a job application."""
        return {
            'title': 'New Job Application',
            'body': f'{applicant_name} applied for "{job_title}"',
            'type': 'job_application',
            'action': 'view_applications'
        }
    
    @staticmethod
    def application_accepted(job_title: str) -> Dict[str, str]:
        """Notification for workers when their application is accepted."""
        return {
            'title': 'Application Accepted! 🎉',
            'body': f'Your application for "{job_title}" has been accepted!',
            'type': 'application_status',
            'status': 'accepted'
        }
    
    @staticmethod
    def application_rejected(job_title: str) -> Dict[str, str]:
        """Notification for workers when their application is rejected."""
        return {
            'title': 'Application Update',
            'body': f'Your application for "{job_title}" was not selected.',
            'type': 'application_status',
            'status': 'rejected'
        }
    
    @staticmethod
    def new_job_match(job_title: str, location: str) -> Dict[str, str]:
        """Notification for workers when a matching job is posted."""
        return {
            'title': 'New Job Match',
            'body': f'New job: "{job_title}" in {location}',
            'type': 'job_match',
            'action': 'view_job'
        }
    
    @staticmethod
    def job_completed(job_title: str) -> Dict[str, str]:
        """Notification when a job is marked as completed."""
        return {
            'title': 'Job Completed',
            'body': f'"{job_title}" has been marked as completed.',
            'type': 'job_status',
            'status': 'completed'
        }
    
    @staticmethod
    def new_review(rating: int, reviewer_name: str) -> Dict[str, str]:
        """Notification when someone leaves a review."""
        stars = '⭐' * rating
        return {
            'title': 'New Review',
            'body': f'{reviewer_name} left you a {rating}-star review {stars}',
            'type': 'review',
            'action': 'view_reviews'
        }
    
    @staticmethod
    def payment_received(amount: str) -> Dict[str, str]:
        """Notification when payment is received."""
        return {
            'title': 'Payment Received 💰',
            'body': f'You received a payment of {amount}',
            'type': 'payment',
            'action': 'view_earnings'
        }
    
    @staticmethod
    def message_received(sender_name: str) -> Dict[str, str]:
        """Notification for new message."""
        return {
            'title': 'New Message',
            'body': f'{sender_name} sent you a message',
            'type': 'message',
            'action': 'open_chat'
        }


# Device token model for storing FCM tokens
class DeviceTokenManager(models.Manager):
    """Manager for DeviceToken model."""
    
    def get_user_tokens(self, user) -> List[str]:
        """Get all active tokens for a user."""
        return list(self.filter(user=user, is_active=True).values_list('token', flat=True))
    
    def register_token(self, user, token: str, device_type: str = 'unknown') -> 'DeviceToken':
        """Register or update a device token for a user."""
        obj, created = self.update_or_create(
            token=token,
            defaults={
                'user': user,
                'device_type': device_type,
                'is_active': True,
            }
        )
        return obj
    
    def deactivate_token(self, token: str) -> bool:
        """Deactivate a device token."""
        updated = self.filter(token=token).update(is_active=False)
        return updated > 0
