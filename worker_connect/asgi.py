"""
ASGI config for worker_connect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import channels routing after Django setup
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from channels.security.websocket import OriginValidator
    from django.conf import settings
    from .routing import websocket_urlpatterns

    class MobileFriendlyOriginValidator(OriginValidator):
        """
        Like channels' AllowedHostsOriginValidator, except a connection with
        NO Origin header at all is let through instead of unconditionally
        rejected. Browsers always send Origin on a WebSocket handshake (same
        origin or cross-origin) - only non-browser clients omit it, e.g.
        React Native's WebSocket implementation, which sent none and was
        being rejected outright in production regardless of a valid auth
        token (verified live via channels.testing.WebsocketCommunicator).
        A malicious browser page attempting Cross-Site WebSocket Hijacking
        DOES send an Origin header, so it's still checked and rejected below
        when it doesn't match ALLOWED_HOSTS - this only widens the "no
        Origin header" case, it doesn't drop origin checking altogether.
        """
        def valid_origin(self, parsed_origin):
            if parsed_origin is None:
                return True
            return self.validate_origin(parsed_origin)

    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": MobileFriendlyOriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
            allowed_hosts,
        ),
    })
except ImportError:
    # Channels not installed, use standard ASGI
    application = django_asgi_app
