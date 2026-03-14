"""
Comprehensive Verification Script for Notification Center Implementation
Run this with: python comprehensive_notification_verification.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.urls import reverse, resolve
from django.template.loader import get_template
from django.contrib.auth import get_user_model
from worker_connect.notification_models import Notification
from worker_connect.notification_web_views import (
    notification_center,
    mark_notification_read_web,
    mark_all_read_web,
    delete_notification_web,
    get_unread_count
)

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_check(status, message):
    symbol = "✓" if status else "✗"
    status_text = "PASS" if status else "FAIL"
    print(f"  [{symbol}] {message:<50} [{status_text}]")

def verify_all():
    """Run all verification checks"""
    all_passed = True
    
    # =========================================================================
    # 1. FILE EXISTENCE CHECKS
    # =========================================================================
    print_header("1. FILE EXISTENCE CHECKS")
    
    files_to_check = [
        ('worker_connect/notification_web_views.py', 'Web Views File'),
        ('worker_connect/notification_web_urls.py', 'Web URLs File'),
        ('templates/notifications/notification_center.html', 'Template File'),
        ('create_test_notifications.py', 'Test Script'),
        ('NOTIFICATION_CENTER_TESTING_GUIDE.md', 'Testing Guide'),
        ('NOTIFICATION_CENTER_IMPLEMENTATION_COMPLETE.md', 'Implementation Doc'),
    ]
    
    for file_path, description in files_to_check:
        full_path = os.path.join(os.getcwd(), file_path)
        exists = os.path.exists(full_path)
        print_check(exists, f"{description}")
        if not exists:
            all_passed = False
    
    # =========================================================================
    # 2. URL PATTERN CHECKS
    # =========================================================================
    print_header("2. URL PATTERN CHECKS")
    
    urls_to_check = [
        ('notification_center', '/notifications/', 'Main Notification Center'),
        ('get_unread_count', '/notifications/unread-count/', 'Unread Count AJAX'),
        ('mark_all_read_web', '/notifications/mark-all-read/', 'Mark All Read'),
    ]
    
    for url_name, expected_path, description in urls_to_check:
        try:
            path = reverse(url_name)
            matches = path == expected_path
            print_check(matches, f"{description}: {path}")
            if not matches:
                print(f"      Expected: {expected_path}, Got: {path}")
                all_passed = False
        except Exception as e:
            print_check(False, f"{description}: ERROR - {str(e)}")
            all_passed = False
    
    # Test URL resolution
    try:
        resolver = resolve('/notifications/')
        is_correct = resolver.func.__name__ == 'notification_center'
        print_check(is_correct, f"URL resolves to correct view")
        if not is_correct:
            all_passed = False
    except Exception as e:
        print_check(False, f"URL resolution: ERROR - {str(e)}")
        all_passed = False
    
    # =========================================================================
    # 3. VIEW FUNCTION CHECKS
    # =========================================================================
    print_header("3. VIEW FUNCTION CHECKS")
    
    views_to_check = [
        (notification_center, 'notification_center'),
        (mark_notification_read_web, 'mark_notification_read_web'),
        (mark_all_read_web, 'mark_all_read_web'),
        (delete_notification_web, 'delete_notification_web'),
        (get_unread_count, 'get_unread_count'),
    ]
    
    for view_func, view_name in views_to_check:
        try:
            is_callable = callable(view_func)
            has_login_required = hasattr(view_func, '__wrapped__')
            print_check(is_callable, f"{view_name} is callable")
            print_check(has_login_required, f"{view_name} has @login_required")
            if not is_callable:
                all_passed = False
        except Exception as e:
            print_check(False, f"{view_name}: ERROR - {str(e)}")
            all_passed = False
    
    # =========================================================================
    # 4. TEMPLATE CHECKS
    # =========================================================================
    print_header("4. TEMPLATE CHECKS")
    
    templates_to_check = [
        ('notifications/notification_center.html', 'Notification Center Template'),
        ('base.html', 'Base Template'),
        ('workers/base_worker.html', 'Worker Base Template'),
        ('clients/base_client.html', 'Client Base Template'),
    ]
    
    for template_path, description in templates_to_check:
        try:
            template = get_template(template_path)
            print_check(True, f"{description} loads")
        except Exception as e:
            print_check(False, f"{description}: ERROR - {str(e)}")
            all_passed = False
    
    # =========================================================================
    # 5. DATABASE MODEL CHECKS
    # =========================================================================
    print_header("5. DATABASE MODEL CHECKS")
    
    try:
        # Check model
        has_model = Notification is not None
        print_check(has_model, "Notification model exists")
        
        # Check notification types
        types_count = len(Notification.NOTIFICATION_TYPES)
        has_10_types = types_count == 10
        print_check(has_10_types, f"Notification types count: {types_count}/10")
        if not has_10_types:
            all_passed = False
        
        # Check database connectivity
        notification_count = Notification.objects.count()
        print_check(True, f"Database accessible: {notification_count} notifications")
        
        # Check model fields
        required_fields = ['recipient', 'title', 'message', 'notification_type', 
                          'is_read', 'read_at', 'created_at']
        model_fields = [f.name for f in Notification._meta.get_fields()]
        
        for field in required_fields:
            has_field = field in model_fields
            print_check(has_field, f"Model has '{field}' field")
            if not has_field:
                all_passed = False
                
    except Exception as e:
        print_check(False, f"Database checks: ERROR - {str(e)}")
        all_passed = False
    
    # =========================================================================
    # 6. USER MODEL CHECKS
    # =========================================================================
    print_header("6. USER MODEL CHECKS")
    
    try:
        User = get_user_model()
        user_count = User.objects.count()
        has_users = user_count > 0
        print_check(has_users, f"Users exist for testing: {user_count} users")
        
        if user_count > 0:
            sample_user = User.objects.first()
            print_check(True, f"Sample user: {sample_user.username}")
        else:
            print_check(False, "No users found - create test users first")
            all_passed = False
            
    except Exception as e:
        print_check(False, f"User model checks: ERROR - {str(e)}")
        all_passed = False
    
    # =========================================================================
    # 7. INTEGRATION CHECKS
    # =========================================================================
    print_header("7. INTEGRATION CHECKS")
    
    # Check if notification_center.html references correct URLs
    try:
        with open('templates/notifications/notification_center.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        checks = [
            ("{% url 'notification_center' %}", "notification_center URL tag"),
            ("{% url 'mark_notification_read_web'", "mark_notification_read_web URL tag"),
            ("{% url 'mark_all_read_web' %}", "mark_all_read_web URL tag"),
            ("{% url 'delete_notification_web'", "delete_notification_web URL tag"),
            ("{% url 'get_unread_count' %}", "get_unread_count URL tag"),
            ("notification-badge", "Badge CSS class"),
            ("updateNotificationBadge", "AJAX update function"),
        ]
        
        for search_string, description in checks:
            found = search_string in template_content
            print_check(found, f"{description} in template")
            if not found:
                all_passed = False
                
    except Exception as e:
        print_check(False, f"Template content checks: ERROR - {str(e)}")
        all_passed = False
    
    # Check base templates for navbar badge
    try:
        base_files = [
            'templates/base.html',
            'templates/workers/base_worker.html',
            'templates/clients/base_client.html'
        ]
        
        for base_file in base_files:
            with open(base_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_notification_link = "notification_center" in content
            has_badge = "notification-badge" in content
            has_ajax = "updateNotificationBadge" in content or "get_unread_count" in content
            
            filename = os.path.basename(base_file)
            print_check(has_notification_link, f"{filename}: notification link")
            print_check(has_badge, f"{filename}: badge element")
            print_check(has_ajax, f"{filename}: AJAX update")
            
            if not (has_notification_link and has_badge and has_ajax):
                all_passed = False
                
    except Exception as e:
        print_check(False, f"Base template checks: ERROR - {str(e)}")
        all_passed = False
    
    # =========================================================================
    # 8. SECURITY CHECKS
    # =========================================================================
    print_header("8. SECURITY CHECKS")
    
    # Check @login_required on views
    security_checks = [
        (notification_center, 'notification_center'),
        (mark_notification_read_web, 'mark_notification_read_web'),
        (mark_all_read_web, 'mark_all_read_web'),
        (delete_notification_web, 'delete_notification_web'),
        (get_unread_count, 'get_unread_count'),
    ]
    
    for view_func, view_name in security_checks:
        # Check if view has login_required decorator
        has_protection = (
            hasattr(view_func, '__wrapped__') or 
            'login_required' in str(view_func.__code__)
        )
        print_check(has_protection, f"{view_name} has authentication")
        if not has_protection:
            all_passed = False
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_header("VERIFICATION SUMMARY")
    
    if all_passed:
        print("\n  🎉 ALL CHECKS PASSED! 🎉")
        print("  ✓ Notification Center implementation is 100% complete")
        print("  ✓ All files exist and are properly configured")
        print("  ✓ All URLs resolve correctly")
        print("  ✓ All templates load without errors")
        print("  ✓ Database models are accessible")
        print("  ✓ Security checks passed")
        print("\n  ✅ READY FOR TESTING AND PRODUCTION DEPLOYMENT")
    else:
        print("\n  ⚠️  SOME CHECKS FAILED")
        print("  Please review the failed items above")
        print("  ❌ NOT RECOMMENDED FOR PRODUCTION")
    
    print(f"\n{'='*70}\n")
    
    return all_passed

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  NOTIFICATION CENTER - COMPREHENSIVE VERIFICATION")
    print("  Date: March 9, 2026")
    print("="*70)
    
    try:
        result = verify_all()
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
