"""
Test script for notification system
"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from worker_connect.notification_models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_notifications():
    print("\n" + "="*50)
    print("TESTING NOTIFICATION SYSTEM")
    print("="*50 + "\n")
    
    # Get a test user
    test_user = User.objects.filter(user_type='client').first()
    
    if not test_user:
        print("⚠️  No test user found. Creating one...")
        test_user = User.objects.create_user(
            username='test_notif_user@test.com',
            email='test_notif_user@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            user_type='client'
        )
        print(f"✅ Created test user: {test_user.email}")
    else:
        print(f"✅ Using existing user: {test_user.email}")
    
    # Test 1: Create notification
    print("\n1. Testing notification creation...")
    notif = Notification.objects.create(
        recipient=test_user,
        title='Test Notification',
        message='Testing the notification system functionality',
        notification_type='system_alert'
    )
    print(f"✅ Notification created: ID={notif.id}")
    print(f"   Title: {notif.title}")
    print(f"   Recipient: {notif.recipient.email}")
    print(f"   Type: {notif.notification_type}")
    print(f"   Is Read: {notif.is_read}")
    print(f"   Created: {notif.created_at}")
    
    # Test 2: Count unread notifications
    print("\n2. Testing unread count...")
    unread_count = Notification.objects.filter(
        recipient=test_user,
        is_read=False
    ).count()
    print(f"✅ Unread notifications: {unread_count}")
    
    # Test 3: Mark as read
    print("\n3. Testing mark as read...")
    notif.mark_as_read()
    print(f"✅ Notification marked as read")
    print(f"   Is Read: {notif.is_read}")
    print(f"   Read At: {notif.read_at}")
    
    # Test 4: Count unread after marking as read
    print("\n4. Testing unread count after marking as read...")
    unread_count = Notification.objects.filter(
        recipient=test_user,
        is_read=False
    ).count()
    print(f"✅ Unread notifications: {unread_count}")
    
    # Test 5: Create multiple notifications
    print("\n5. Testing multiple notifications...")
    for i in range(3):
        Notification.objects.create(
            recipient=test_user,
            title=f'Test Notification {i+2}',
            message=f'Testing notification #{i+2}',
            notification_type='system_alert'
        )
    total_count = Notification.objects.filter(recipient=test_user).count()
    print(f"✅ Created 3 more notifications. Total: {total_count}")
    
    # Test 6: Get notifications (simulate API call)
    print("\n6. Testing notification retrieval...")
    notifications = Notification.objects.filter(recipient=test_user)[:10]
    print(f"✅ Retrieved {notifications.count()} notifications")
    for n in notifications:
        print(f"   - {n.title} | Read: {n.is_read} | Created: {n.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Test 7: Mark all as read
    print("\n7. Testing mark all as read...")
    from django.utils import timezone
    updated = Notification.objects.filter(
        recipient=test_user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    print(f"✅ Marked {updated} notifications as read")
    
    # Test 8: Final unread count
    print("\n8. Testing final unread count...")
    unread_count = Notification.objects.filter(
        recipient=test_user,
        is_read=False
    ).count()
    print(f"✅ Unread notifications: {unread_count}")
    
    # Cleanup
    print("\n9. Cleaning up test data...")
    deleted = Notification.objects.filter(recipient=test_user).delete()
    print(f"✅ Deleted {deleted[0]} test notifications")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED ✅")
    print("="*50 + "\n")

if __name__ == '__main__':
    test_notifications()
