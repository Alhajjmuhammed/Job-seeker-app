"""
Script to create test notifications for testing the Notification Center UI
Run this with: python manage.py shell < create_test_notifications.py
"""
from django.contrib.auth import get_user_model
from worker_connect.notification_models import Notification
from django.utils import timezone

User = get_user_model()

def create_test_notifications():
    """Create test notifications for all users"""
    
    # Get all users (or you can specify a specific user)
    users = User.objects.all()[:5]  # Get first 5 users for testing
    
    if not users:
        print("❌ No users found. Please create users first.")
        return
    
    notification_data = [
        {
            'notification_type': 'job_assigned',
            'title': 'New Job Assignment',
            'message': 'You have been assigned to a plumbing job at 123 Main St.'
        },
        {
            'notification_type': 'message_received',
            'title': 'New Message',
            'message': 'John Smith sent you a message about your application.'
        },
        {
            'notification_type': 'payment_received',
            'title': 'Payment Received',
            'message': 'You received $150.00 for Job #12345.'
        },
        {
            'notification_type': 'review_received',
            'title': 'New Review',
            'message': 'Sarah Johnson left you a 5-star review!'
        },
        {
            'notification_type': 'job_completed',
            'title': 'Job Completed',
            'message': 'Congratulations! You completed the electrical work successfully.'
        },
        {
            'notification_type': 'document_verified',
            'title': 'Document Verified',
            'message': 'Your license document has been verified by the admin.'
        },
        {
            'notification_type': 'system_alert',
            'title': 'System Maintenance',
            'message': 'Scheduled maintenance on Sunday 2AM-4AM. Services may be unavailable.'
        },
        {
            'notification_type': 'promotion',
            'title': 'Special Offer!',
            'message': 'Upgrade to Premium and get 20% off for the first month!'
        },
        {
            'notification_type': 'job_application',
            'title': 'Application Submitted',
            'message': 'Your application for Construction Job has been submitted successfully.'
        },
        {
            'notification_type': 'account_update',
            'title': 'Profile Updated',
            'message': 'Your profile information has been updated successfully.'
        },
    ]
    
    created_count = 0
    
    for user in users:
        print(f"\n Creating notifications for {user.username}...")
        
        # Create all types of notifications
        for i, notif_data in enumerate(notification_data):
            notification = Notification.objects.create(
                recipient=user,
                title=notif_data['title'],
                message=notif_data['message'],
                notification_type=notif_data['notification_type'],
                is_read=(i % 3 == 0),  # Mark every 3rd notification as read
                created_at=timezone.now()
            )
            created_count += 1
            
            # Mark some as read with read_at timestamp
            if notification.is_read:
                notification.read_at = timezone.now()
                notification.save()
                print(f"   ✓ Created READ: {notification.title}")
            else:
                print(f"   ✓ Created UNREAD: {notification.title}")
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully created {created_count} test notifications!")
    print(f"{'='*60}")
    print(f"📊 Distribution:")
    print(f"   - Total users: {users.count()}")
    print(f"   - Notifications per user: {len(notification_data)}")
    print(f"   - Total notifications: {created_count}")
    print(f"\n💡 Tip: Visit /notifications/ to see the notification center!")

if __name__ == '__main__':
    create_test_notifications()
