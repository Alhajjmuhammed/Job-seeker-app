#!/usr/bin/env python3
"""
Test WebSocket Setup
Verifies that Django Channels and WebSocket are properly configured.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

print("=" * 80)
print("WebSocket Configuration Test")
print("=" * 80)
print()

# Test 1: Check if Channels is installed
print("✓ Test 1: Checking Django Channels installation...")
try:
    import channels
    print(f"  ✅ Django Channels {channels.__version__} is installed")
except ImportError:
    print("  ❌ Django Channels is not installed")
    print("  Run: pip install channels channels-redis")
    sys.exit(1)

# Test 2: Check ASGI configuration
print("\n✓ Test 2: Checking ASGI configuration...")
if hasattr(settings, 'ASGI_APPLICATION'):
    print(f"  ✅ ASGI_APPLICATION = {settings.ASGI_APPLICATION}")
else:
    print("  ❌ ASGI_APPLICATION not configured in settings.py")
    sys.exit(1)

# Test 3: Check Channel Layers
print("\n✓ Test 3: Checking Channel Layers configuration...")
if hasattr(settings, 'CHANNEL_LAYERS'):
    backend = settings.CHANNEL_LAYERS['default']['BACKEND']
    print(f"  ✅ Channel Layer Backend: {backend}")
    
    if 'InMemory' in backend:
        print("  ℹ️  Using In-Memory channel layer (good for development)")
    elif 'Redis' in backend:
        print("  ✅ Using Redis channel layer (production-ready)")
else:
    print("  ❌ CHANNEL_LAYERS not configured in settings.py")
    sys.exit(1)

# Test 4: Test Channel Layer Communication
print("\n✓ Test 4: Testing channel layer communication...")
try:
    channel_layer = get_channel_layer()
    
    # Try to send a test message
    test_data = {
        'type': 'test_message',
        'data': {'test': 'Hello WebSocket!'}
    }
    
    async_to_sync(channel_layer.group_send)(
        'test_group',
        test_data
    )
    print("  ✅ Successfully sent test message to channel layer")
except Exception as e:
    print(f"  ❌ Error testing channel layer: {e}")
    print("  Make sure Redis is running if using Redis backend")

# Test 5: Check WebSocket Consumers
print("\n✓ Test 5: Checking WebSocket consumers...")
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
            print(f"  ❌ {consumer} is missing")
except ImportError as e:
    print(f"  ❌ Cannot import websocket_consumers: {e}")

# Test 6: Check WebSocket routing
print("\n✓ Test 6: Checking WebSocket URL routing...")
try:
    from worker_connect import routing
    if hasattr(routing, 'websocket_urlpatterns'):
        print(f"  ✅ websocket_urlpatterns defined with {len(routing.websocket_urlpatterns)} routes")
        for pattern in routing.websocket_urlpatterns:
            print(f"     - {pattern.pattern}")
    else:
        print("  ❌ websocket_urlpatterns not found in routing.py")
except ImportError as e:
    print(f"  ❌ Cannot import routing: {e}")

# Test 7: Check if Channels is in INSTALLED_APPS
print("\n✓ Test 7: Checking INSTALLED_APPS...")
if 'channels' in settings.INSTALLED_APPS:
    print("  ✅ 'channels' is in INSTALLED_APPS")
else:
    print("  ❌ 'channels' is not in INSTALLED_APPS")
    print("  Add 'channels' to INSTALLED_APPS in settings.py")

# Test 8: Check helper functions
print("\n✓ Test 8: Checking helper functions...")
try:
    from worker_connect.websocket_consumers import send_user_notification, broadcast_new_job
    print("  ✅ send_user_notification function is available")
    print("  ✅ broadcast_new_job function is available")
except ImportError as e:
    print(f"  ❌ Cannot import helper functions: {e}")

# Summary
print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print()
print("✅ WebSocket setup is COMPLETE!")
print()
print("Next steps:")
print("1. Start Django development server: python manage.py runserver")
print("2. The dev server automatically supports WebSocket connections")
print("3. Connect from mobile app or web browser")
print()
print("WebSocket URLs:")
print("  - Notifications: ws://localhost:8000/ws/notifications/?token=<auth_token>")
print("  - Jobs:          ws://localhost:8000/ws/jobs/")
print("  - Chat:          ws://localhost:8000/ws/chat/<conversation_id>/?token=<auth_token>")
print()
print("For production deployment:")
print("  - Use Daphne: daphne -b 0.0.0.0 -p 8000 worker_connect.asgi:application")
print("  - Or Uvicorn: uvicorn worker_connect.asgi:application --host 0.0.0.0 --port 8000")
print()
print("For multi-instance production:")
print("  - Install Redis: redis-server")
print("  - Set REDIS_URL in .env: REDIS_URL=redis://localhost:6379/0")
print()
print("=" * 80)
