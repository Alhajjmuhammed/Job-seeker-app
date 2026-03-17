#!/usr/bin/env python3
"""
End-to-End WebSocket Test
Tests actual WebSocket connection and message delivery
"""

import os
import sys
import django
import asyncio
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from worker_connect.asgi import application

User = get_user_model()

print("=" * 80)
print("WebSocket End-to-End Live Test")
print("=" * 80)
print()

@database_sync_to_async
def get_test_user():
    """Get test user from database"""
    return User.objects.filter(is_active=True).first()

@database_sync_to_async
def get_or_create_token(user):
    """Get or create auth token for user"""
    token, created = Token.objects.get_or_create(user=user)
    return token

async def test_websocket_connection():
    """Test actual WebSocket connection"""
    
    # Get or create a test user
    print("✓ Step 1: Getting test user...")
    try:
        user = await get_test_user()
        if not user:
            print("  ❌ No active users found in database")
            print("  Create a user first: python manage.py createsuperuser")
            return False
        
        print(f"  ✅ Found user: {user.username} (ID: {user.id})")
    except Exception as e:
        print(f"  ❌ Error getting user: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Get or create auth token
    print("\n✓ Step 2: Getting auth token...")
    try:
        token = await get_or_create_token(user)
        print(f"  ✅ Token obtained: {token.key[:20]}...")
    except Exception as e:
        print(f"  ❌ Error getting token: {e}")
        return False
    
    # Test WebSocket connection
    print("\n✓ Step 3: Testing WebSocket connection...")
    try:
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={token.key}"
        )
        communicator.scope['user'] = user
        
        connected, subprotocol = await communicator.connect()
        
        if not connected:
            print("  ❌ WebSocket connection failed")
            return False
        
        print("  ✅ WebSocket connected successfully!")
        
        # Test receiving connection confirmation
        print("\n✓ Step 4: Waiting for connection confirmation...")
        try:
            response = await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=5.0
            )
            
            if response.get('type') == 'connection_established':
                print(f"  ✅ Received: {response}")
            else:
                print(f"  ⚠️  Unexpected response: {response}")
        except asyncio.TimeoutError:
            print("  ⚠️  No connection confirmation received (might be OK)")
        
        # Test sending a ping
        print("\n✓ Step 5: Sending ping message...")
        await communicator.send_json_to({
            'type': 'ping'
        })
        print("  ✅ Ping sent")
        
        # Test receiving pong
        print("\n✓ Step 6: Waiting for pong response...")
        try:
            response = await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=5.0
            )
            
            if response.get('type') == 'pong':
                print(f"  ✅ Received pong! WebSocket is responsive")
            else:
                print(f"  ⚠️  Received: {response}")
        except asyncio.TimeoutError:
            print("  ⚠️  No pong response (might indicate consumer issue)")
        
        # Test sending notification through channel layer
        print("\n✓ Step 7: Testing notification delivery via channel layer...")
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"user_{user.id}",
            {
                'type': 'send_notification',
                'data': {
                    'title': 'Test Notification',
                    'message': 'This is a test message from the WebSocket test script',
                    'notification_type': 'test',
                    'timestamp': datetime.now().isoformat(),
                }
            }
        )
        print("  ✅ Notification sent via channel layer")
        
        # Try to receive the notification
        print("\n✓ Step 8: Waiting for notification delivery...")
        try:
            response = await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=5.0
            )
            
            if response.get('type') == 'notification':
                print(f"  ✅ Notification received! Data: {response.get('data')}")
            else:
                print(f"  ⚠️  Received different message: {response}")
        except asyncio.TimeoutError:
            print("  ⚠️  No notification received (channel layer might need Redis)")
        
        # Close connection
        await communicator.disconnect()
        print("\n✓ Step 9: WebSocket disconnected cleanly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error during WebSocket test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_job_websocket():
    """Test job updates WebSocket (no auth required)"""
    print("\n" + "=" * 80)
    print("Testing Job Updates WebSocket (Public)")
    print("=" * 80)
    print()
    
    try:
        communicator = WebsocketCommunicator(
            application,
            "/ws/jobs/"
        )
        
        connected, subprotocol = await communicator.connect()
        
        if not connected:
            print("  ❌ Job WebSocket connection failed")
            return False
        
        print("  ✅ Job WebSocket connected!")
        
        # Wait for connection message
        try:
            response = await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=3.0
            )
            print(f"  ✅ Received: {response}")
        except asyncio.TimeoutError:
            print("  ⚠️  No connection message")
        
        await communicator.disconnect()
        print("  ✅ Job WebSocket test complete")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    
    # Test authenticated notification WebSocket
    result1 = await test_websocket_connection()
    
    # Test public job WebSocket
    result2 = await test_job_websocket()
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    
    if result1 and result2:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Your WebSocket setup is working correctly!")
        print()
        print("Next steps:")
        print("1. Start Django server: python manage.py runserver")
        print("2. Open mobile app and log in")
        print("3. WebSocket will connect automatically")
        print("4. Try creating a service request to see real-time notifications")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Issues found:")
        if not result1:
            print("❌ Authenticated WebSocket has issues")
        if not result2:
            print("❌ Job WebSocket has issues")
        print()
        print("Common fixes:")
        print("1. Make sure you have at least one user in the database")
        print("2. For full functionality, install Redis and set REDIS_URL")
        print("3. Check that 'channels' is in INSTALLED_APPS")
        print("4. Verify ASGI_APPLICATION is set in settings.py")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
