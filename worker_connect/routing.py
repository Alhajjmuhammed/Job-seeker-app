"""
WebSocket URL routing for Worker Connect.
"""

from django.urls import re_path
from . import websocket_consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', websocket_consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/jobs/$', websocket_consumers.JobUpdatesConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', websocket_consumers.ChatConsumer.as_asgi()),
]
