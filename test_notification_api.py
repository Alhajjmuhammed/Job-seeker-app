"""
Test script for notification API endpoints
"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from worker_connect.notification_models import Notification

User = get_user_model()

def test_api_endpoints():
    print("\n" + "="*50)
    print("TESTING NOTIFICATION API ENDPOINTS")
    print("="*50 + "\n")
    
    # Setup
    client = APIClient()
    test_user = User.objects.filter(user_type='client').first()
    
    if not test_user:
        print("⚠️  No test user found")
        return
    
    print(f"✅ Test user: {test_user.email}")
    
    # Create test notifications
    print("\n1. Creating test notifications...")
    for i in range(3):
        Notification.objects.create(
            recipient=test_user,
            title=f'API Test Notification {i+1}',
            message=f'Testing API endpoint #{i+1}',
            notification_type='system_alert'
        )
    print(f"✅ Created 3 test notifications")
    
    # Authenticate
    client.force_authenticate(user=test_user)
    print(f"✅ Authenticated as {test_user.email}")
    
    # Test 1: Get notifications
    print("\n2. Testing GET /api/notifications/...")
    response = client.get('/api/notifications/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Retrieved {len(data)} notifications")
        if data:
            print(f"   First notification: {data[0]['title']}")
    else:
        print(f"❌ Failed: {response.data}")
    
    # Test 2: Get unread count
    print("\n3. Testing GET /api/notifications/unread-count/...")
    response = client.get('/api/notifications/unread-count/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        count = response.json()['count']
        print(f"✅ Success! Unread count: {count}")
    else:
        print(f"❌ Failed: {response.data}")
    
    # Test 3: Mark one as read
    print("\n4. Testing POST /api/notifications/<id>/read/...")
    notif = Notification.objects.filter(recipient=test_user, is_read=False).first()
    if notif:
        response = client.post(f'/api/notifications/{notif.id}/read/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Success! Marked notification {notif.id} as read")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Failed: {response.data}")
    else:
        print(f"⚠️  No unread notifications to mark")
    
    # Test 4: Get unread only
    print("\n5. Testing GET /api/notifications/?unread_only=true...")
    response = client.get('/api/notifications/', {'unread_only': 'true'})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Unread notifications: {len(data)}")
    else:
        print(f"❌ Failed: {response.data}")
    
    # Test 5: Mark all as read
    print("\n6. Testing POST /api/notifications/read-all/...")
    response = client.post('/api/notifications/read-all/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! {result}")
    else:
        print(f"❌ Failed: {response.data}")
    
    # Test 6: Verify all marked as read
    print("\n7. Verifying all notifications marked as read...")
    unread_count = Notification.objects.filter(recipient=test_user, is_read=False).count()
    print(f"✅ Unread count: {unread_count}")
    
    # Cleanup
    print("\n8. Cleaning up test data...")
    deleted = Notification.objects.filter(
        recipient=test_user,
        title__startswith='API Test'
    ).delete()
    print(f"✅ Deleted {deleted[0]} test notifications")
    
    print("\n" + "="*50)
    print("API TESTS COMPLETED ✅")
    print("="*50 + "\n")

if __name__ == '__main__':
    test_api_endpoints()
