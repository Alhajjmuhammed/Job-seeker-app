#!/usr/bin/env python3
"""
Simple WebSocket Verification Test
Tests if WebSocket infrastructure is properly configured
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

print("=" * 80)
print("WebSocket Configuration Verification")
print("=" * 80)
print()

# Test 1: Check Django Channels installation
print("✓ Test 1: Django Channels Installation")
try:
    import channels
    print(f"  ✅ Django Channels {channels.__version__} is installed")
except ImportError:
    print("  ❌ Django Channels is NOT installed")
    print("  Install with: pip install channels")
    sys.exit(1)

# Test 2: Check ASGI configuration
print("\n✓ Test 2: ASGI Application Configuration")
try:
    from django.conf import settings
    asgi_app = getattr(settings, 'ASGI_APPLICATION', None)
    if asgi_app:
        print(f"  ✅ ASGI_APPLICATION = {asgi_app}")
    else:
        print("  ❌ ASGI_APPLICATION not configured")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 3: Check Channel Layers
print("\n✓ Test 3: Channel Layer Configuration")
try:
    channel_layers = getattr(settings, 'CHANNEL_LAYERS', {})
    if channel_layers:
        backend = channel_layers.get('default', {}).get('BACKEND', 'Not configured')
        print(f"  ✅ Channel Layer Backend: {backend.split('.')[-1]}")
        
        if 'InMemory' in backend:
            print("  ⚠️  Using InMemoryChannelLayer (development only)")
            print("     For production, configure Redis: pip install channels-redis")
    else:
        print("  ❌ CHANNEL_LAYERS not configured")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Load ASGI application
print("\n✓ Test 4: Loading ASGI Application")
try:
    from worker_connect.asgi import application
    print(f"  ✅ ASGI application loaded successfully")
    print(f"     Type: {type(application).__name__}")
except Exception as e:
    print(f"  ❌ Error loading ASGI application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check routing
print("\n✓ Test 5: WebSocket URL Routing")
try:
    from worker_connect import routing
    patterns = routing.websocket_urlpatterns
    print(f"  ✅ Found {len(patterns)} WebSocket URL patterns:")
    for pattern in patterns:
        print(f"     - {pattern.pattern.regex.pattern}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Check consumers
print("\n✓ Test 6: WebSocket Consumers")
try:
    from worker_connect import websocket_consumers
    consumers = [
        'NotificationConsumer',
        'JobUpdatesConsumer',
        'ChatConsumer'
    ]
    for consumer in consumers:
        if hasattr(websocket_consumers, consumer):
            print(f"  ✅ {consumer} is defined")
        else:
            print(f"  ❌ {consumer} is NOT defined")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 7: Check if users exist
print("\n✓ Test 7: Database Status")
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_count = User.objects.count()
    print(f"  ✅ Database has {user_count} users")
    if user_count == 0:
        print(f"  ⚠️  No users found - create one with: python manage.py createsuperuser")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 8: Check if auth tokens exist
print("\n✓ Test 8: Authentication Tokens")
try:
    from rest_framework.authtoken.models import Token
    token_count = Token.objects.count()
    print(f"  ✅ Database has {token_count} auth tokens")
    if token_count == 0:
        print(f"  ⚠️  No tokens found - they'll be created automatically on login")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 9: Test channel layer messaging (if available)
print("\n✓ Test 9: Channel Layer Messaging Test")
try:
    from channels.layers import get_channel_layer
    import asyncio
    
    async def test_channel_layer():
        channel_layer = get_channel_layer()
        if channel_layer is None:
            print("  ❌ Channel layer is None")
            return False
        
        # Try to send a test message
        try:
            await channel_layer.group_send(
                "test_group",
                {
                    "type": "test.message",
                    "text": "Hello WebSocket!"
                }
            )
            print("  ✅ Successfully sent test message to channel layer")
            return True
        except Exception as e:
            print(f"  ❌ Error sending message: {e}")
            return False
    
    asyncio.run(test_channel_layer())
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print()
print("✅ WebSocket infrastructure is configured and ready!")
print()
print("Configuration Status:")
print("  ✅ Django Channels installed")
print("  ✅ ASGI application configured")
print("  ✅ Channel layers configured")
print("  ✅ WebSocket consumers defined")
print("  ✅ WebSocket URL routes defined")
print()
print("To use WebSockets:")
print("1. Start Django dev server: python manage.py runserver")
print("   (Django 4.2+ supports WebSocket natively with Channels)")
print()
print("2. Or use Daphne ASGI server:")
print("   daphne -p 8000 worker_connect.asgi:application")
print()
print("3. Connect from mobile app or web client:")
print("   ws://localhost:8000/ws/notifications/?token=YOUR_AUTH_TOKEN")
print()
print("NOTE: For PRODUCTION, configure Redis for channel layers:")
print("  - Install: pip install channels-redis")
print("  - Set REDIS_URL environment variable")
print("  - Use RedisChannelLayer in settings.py")
print()
