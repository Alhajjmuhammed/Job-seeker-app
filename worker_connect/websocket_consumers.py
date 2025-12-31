"""
WebSocket consumers for real-time notifications.

Requires Django Channels. Install with:
    pip install channels channels-redis

Add to INSTALLED_APPS: 'channels'
Set ASGI_APPLICATION = 'worker_connect.asgi.application'
"""

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time user notifications.
    
    Connect: ws://host/ws/notifications/
    Authentication: Pass token in query string: ?token=<auth_token>
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Get token from query string
        token = self.scope.get('query_string', b'').decode()
        token = dict(x.split('=') for x in token.split('&') if '=' in x).get('token', '')
        
        # Authenticate user
        self.user = await self.get_user_from_token(token)
        
        if self.user is None:
            await self.close(code=4001)
            return
        
        # Join user's personal notification group
        self.room_group_name = f'user_{self.user.id}_notifications'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send_json({
            'type': 'connection_established',
            'message': 'Connected to notification service',
            'user_id': self.user.id,
        })
        
        logger.info(f"WebSocket connected for user {self.user.id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for user {getattr(self, 'user', 'unknown')}")
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        message_type = content.get('type', '')
        
        if message_type == 'ping':
            await self.send_json({'type': 'pong'})
        elif message_type == 'mark_read':
            notification_id = content.get('notification_id')
            if notification_id:
                await self.mark_notification_read(notification_id)
                await self.send_json({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id
                })
    
    async def notification_message(self, event):
        """Send notification to WebSocket."""
        await self.send_json({
            'type': 'notification',
            'data': event['data'],
        })
    
    async def job_update(self, event):
        """Send job update notification."""
        await self.send_json({
            'type': 'job_update',
            'data': event['data'],
        })
    
    async def application_update(self, event):
        """Send application status update."""
        await self.send_json({
            'type': 'application_update',
            'data': event['data'],
        })
    
    async def message_received(self, event):
        """Send new message notification."""
        await self.send_json({
            'type': 'new_message',
            'data': event['data'],
        })
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Authenticate user from token."""
        from rest_framework.authtoken.models import Token
        try:
            token_obj = Token.objects.select_related('user').get(key=token)
            return token_obj.user
        except Token.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        # Implement based on your notification model
        pass


class JobUpdatesConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time job updates.
    Workers can subscribe to get notified about new jobs.
    
    Connect: ws://host/ws/jobs/
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Public channel for job updates
        self.room_group_name = 'job_updates'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send_json({
            'type': 'connection_established',
            'message': 'Connected to job updates',
        })
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        """Handle incoming messages."""
        message_type = content.get('type', '')
        
        if message_type == 'subscribe_location':
            # Subscribe to location-specific updates
            location = content.get('location', '').lower().replace(' ', '_')
            if location:
                await self.channel_layer.group_add(
                    f'jobs_{location}',
                    self.channel_name
                )
                await self.send_json({
                    'type': 'subscribed',
                    'location': location
                })
    
    async def new_job(self, event):
        """Broadcast new job posting."""
        await self.send_json({
            'type': 'new_job',
            'data': event['data'],
        })
    
    async def job_updated(self, event):
        """Broadcast job update."""
        await self.send_json({
            'type': 'job_updated',
            'data': event['data'],
        })


# Helper functions to send notifications from views/signals
def send_user_notification(user_id: int, notification_data: dict):
    """
    Send notification to a specific user via WebSocket.
    
    Usage:
        from worker_connect.websocket_consumers import send_user_notification
        send_user_notification(user.id, {
            'title': 'New Application',
            'message': 'Someone applied to your job',
            'type': 'application',
        })
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}_notifications',
            {
                'type': 'notification_message',
                'data': notification_data,
            }
        )


def broadcast_new_job(job_data: dict, location: str = None):
    """
    Broadcast new job to all connected clients.
    
    Usage:
        broadcast_new_job({
            'id': job.id,
            'title': job.title,
            'location': job.location,
        })
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if channel_layer:
        # Send to general job updates channel
        async_to_sync(channel_layer.group_send)(
            'job_updates',
            {
                'type': 'new_job',
                'data': job_data,
            }
        )
        
        # Also send to location-specific channel if provided
        if location:
            location_channel = f'jobs_{location.lower().replace(" ", "_")}'
            async_to_sync(channel_layer.group_send)(
                location_channel,
                {
                    'type': 'new_job',
                    'data': job_data,
                }
            )
