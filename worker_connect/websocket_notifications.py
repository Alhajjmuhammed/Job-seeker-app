"""
WebSocket notification service for Worker Connect.

This module provides real-time notifications via WebSocket connections.
"""

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Create user-specific group
        self.user_group = f"user_{self.user.id}"
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )
        
        # Join role-specific groups
        user_role = await self.get_user_role()
        if user_role:
            self.role_group = f"role_{user_role}"
            await self.channel_layer.group_add(
                self.role_group,
                self.channel_name
            )
        
        # Join global broadcast group
        await self.channel_layer.group_add(
            "broadcast",
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send_json({
            'type': 'connection_established',
            'user_id': self.user.id,
            'groups': [self.user_group],
        })
        
        # Send unread notification count
        unread_count = await self.get_unread_count()
        await self.send_json({
            'type': 'unread_count',
            'count': unread_count,
        })
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
        
        if hasattr(self, 'role_group'):
            await self.channel_layer.group_discard(
                self.role_group,
                self.channel_name
            )
        
        await self.channel_layer.group_discard(
            "broadcast",
            self.channel_name
        )
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        message_type = content.get('type')
        
        if message_type == 'mark_read':
            notification_id = content.get('notification_id')
            await self.mark_notification_read(notification_id)
        
        elif message_type == 'mark_all_read':
            await self.mark_all_read()
        
        elif message_type == 'subscribe':
            # Subscribe to additional groups
            group = content.get('group')
            if group:
                await self.channel_layer.group_add(group, self.channel_name)
        
        elif message_type == 'unsubscribe':
            group = content.get('group')
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)
        
        elif message_type == 'ping':
            await self.send_json({'type': 'pong'})
    
    # Event handlers for different notification types
    
    async def notification(self, event):
        """Handle notification event."""
        await self.send_json({
            'type': 'notification',
            'data': event['data'],
        })
    
    async def job_update(self, event):
        """Handle job update event."""
        await self.send_json({
            'type': 'job_update',
            'data': event['data'],
        })
    
    async def message_received(self, event):
        """Handle new message event."""
        await self.send_json({
            'type': 'message_received',
            'data': event['data'],
        })
    
    async def application_status(self, event):
        """Handle job application status event."""
        await self.send_json({
            'type': 'application_status',
            'data': event['data'],
        })
    
    async def payment_update(self, event):
        """Handle payment update event."""
        await self.send_json({
            'type': 'payment_update',
            'data': event['data'],
        })
    
    async def broadcast_message(self, event):
        """Handle broadcast message event."""
        await self.send_json({
            'type': 'broadcast',
            'data': event['data'],
        })
    
    # Database operations
    
    @database_sync_to_async
    def get_user_role(self):
        """Get user's role (worker/client)."""
        if hasattr(self.user, 'worker_profile'):
            return 'worker'
        if hasattr(self.user, 'client_profile'):
            return 'client'
        return None
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread notifications."""
        try:
            from jobs.activity import Activity
            return Activity.objects.filter(
                user=self.user,
                is_read=False
            ).count()
        except:
            return 0
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        try:
            from jobs.activity import Activity
            Activity.objects.filter(
                id=notification_id,
                user=self.user
            ).update(is_read=True)
        except:
            pass
    
    @database_sync_to_async
    def mark_all_read(self):
        """Mark all notifications as read."""
        try:
            from jobs.activity import Activity
            Activity.objects.filter(
                user=self.user,
                is_read=False
            ).update(is_read=True)
        except:
            pass


class NotificationService:
    """
    Service for sending notifications via WebSocket.
    """
    
    @staticmethod
    def get_channel_layer():
        """Get the channel layer."""
        return get_channel_layer()
    
    @staticmethod
    def send_to_user(user_id, notification_type, data):
        """
        Send notification to a specific user.
        """
        channel_layer = NotificationService.get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                'type': notification_type,
                'data': data,
            }
        )
    
    @staticmethod
    def send_to_group(group_name, notification_type, data):
        """
        Send notification to a group.
        """
        channel_layer = NotificationService.get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': notification_type,
                'data': data,
            }
        )
    
    @staticmethod
    def broadcast(notification_type, data):
        """
        Broadcast notification to all connected users.
        """
        channel_layer = NotificationService.get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "broadcast",
            {
                'type': 'broadcast_message',
                'data': data,
            }
        )
    
    # Convenience methods for common notifications
    
    @staticmethod
    def notify_job_application(client_id, job_id, worker_name):
        """Notify client of new job application."""
        NotificationService.send_to_user(
            client_id,
            'notification',
            {
                'title': 'New Job Application',
                'message': f'{worker_name} applied to your job',
                'job_id': job_id,
                'action': 'view_application',
            }
        )
    
    @staticmethod
    def notify_application_status(worker_id, job_id, status):
        """Notify worker of application status change."""
        NotificationService.send_to_user(
            worker_id,
            'application_status',
            {
                'title': f'Application {status.title()}',
                'message': f'Your application has been {status}',
                'job_id': job_id,
                'status': status,
            }
        )
    
    @staticmethod
    def notify_job_assigned(worker_id, job_id, job_title):
        """Notify worker of job assignment."""
        NotificationService.send_to_user(
            worker_id,
            'job_update',
            {
                'title': 'Job Assigned',
                'message': f'You have been assigned to: {job_title}',
                'job_id': job_id,
                'action': 'view_job',
            }
        )
    
    @staticmethod
    def notify_new_message(user_id, sender_name, message_preview):
        """Notify user of new message."""
        NotificationService.send_to_user(
            user_id,
            'message_received',
            {
                'title': 'New Message',
                'message': f'{sender_name}: {message_preview[:50]}...',
                'action': 'view_messages',
            }
        )
    
    @staticmethod
    def notify_payment(worker_id, amount, job_id=None):
        """Notify worker of payment received."""
        NotificationService.send_to_user(
            worker_id,
            'payment_update',
            {
                'title': 'Payment Received',
                'message': f'You received a payment of ${amount}',
                'amount': str(amount),
                'job_id': job_id,
            }
        )
    
    @staticmethod
    def notify_review(user_id, reviewer_name, rating):
        """Notify user of new review."""
        NotificationService.send_to_user(
            user_id,
            'notification',
            {
                'title': 'New Review',
                'message': f'{reviewer_name} left you a {rating}-star review',
                'rating': rating,
                'action': 'view_reviews',
            }
        )


# WebSocket routing
from django.urls import re_path

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]
