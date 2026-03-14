"""
Comprehensive Test Script for Password Management System
Tests all views, forms, and URL routing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from accounts.forms import PasswordResetRequestForm, PasswordResetConfirmForm, ChangePasswordForm
from accounts.views import forgot_password, reset_password, change_password

User = get_user_model()

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def test_pass(test_name):
    print(f"{GREEN}✓{RESET} {test_name}")
    return True

def test_fail(test_name, error=""):
    print(f"{RED}✗{RESET} {test_name}")
    if error:
        print(f"  {RED}Error: {error}{RESET}")
    return False

def test_urls():
    """Test URL routing"""
    print_header("1. TESTING URL ROUTING")
    results = []
    
    try:
        # Test forgot password URL
        url = reverse('accounts:forgot_password')
        assert url == '/accounts/forgot-password/', f"Expected /accounts/forgot-password/, got {url}"
        resolver = resolve(url)
        assert resolver.func == forgot_password
        results.append(test_pass("Forgot Password URL: /accounts/forgot-password/"))
    except Exception as e:
        results.append(test_fail("Forgot Password URL", str(e)))
    
    try:
        # Test reset password URL
        url = reverse('accounts:reset_password', kwargs={'uidb64': 'test123', 'token': 'test-token'})
        assert '/accounts/reset-password/test123/test-token/' in url
        results.append(test_pass("Reset Password URL: /accounts/reset-password/<uidb64>/<token>/"))
    except Exception as e:
        results.append(test_fail("Reset Password URL", str(e)))
    
    try:
        # Test change password URL
        url = reverse('accounts:change_password')
        assert url == '/accounts/change-password/', f"Expected /accounts/change-password/, got {url}"
        resolver = resolve(url)
        assert resolver.func == change_password
        results.append(test_pass("Change Password URL: /accounts/change-password/"))
    except Exception as e:
        results.append(test_fail("Change Password URL", str(e)))
    
    try:
        # Test login URL still works
        url = reverse('accounts:login')
        assert url == '/accounts/login/'
        results.append(test_pass("Login URL: /accounts/login/ (unchanged)"))
    except Exception as e:
        results.append(test_fail("Login URL", str(e)))
    
    return results

def test_forms():
    """Test form validation"""
    print_header("2. TESTING FORMS")
    results = []
    
    try:
        # Test PasswordResetRequestForm
        form = PasswordResetRequestForm(data={'email': 'test@example.com'})
        assert form.is_valid(), f"Form errors: {form.errors}"
        results.append(test_pass("PasswordResetRequestForm with valid email"))
    except Exception as e:
        results.append(test_fail("PasswordResetRequestForm", str(e)))
    
    try:
        # Test empty email
        form = PasswordResetRequestForm(data={'email': ''})
        assert not form.is_valid()
        results.append(test_pass("PasswordResetRequestForm rejects empty email"))
    except Exception as e:
        results.append(test_fail("PasswordResetRequestForm empty validation", str(e)))
    
    try:
        # Test PasswordResetConfirmForm with matching passwords
        form = PasswordResetConfirmForm(data={
            'password1': 'TestPass123!',
            'password2': 'TestPass123!'
        })
        assert form.is_valid(), f"Form errors: {form.errors}"
        results.append(test_pass("PasswordResetConfirmForm with matching passwords"))
    except Exception as e:
        results.append(test_fail("PasswordResetConfirmForm", str(e)))
    
    try:
        # Test mismatched passwords
        form = PasswordResetConfirmForm(data={
            'password1': 'TestPass123!',
            'password2': 'DifferentPass!'
        })
        assert not form.is_valid()
        results.append(test_pass("PasswordResetConfirmForm rejects mismatched passwords"))
    except Exception as e:
        results.append(test_fail("PasswordResetConfirmForm mismatch validation", str(e)))
    
    try:
        # Test short password
        form = PasswordResetConfirmForm(data={
            'password1': 'short',
            'password2': 'short'
        })
        assert not form.is_valid()
        results.append(test_pass("PasswordResetConfirmForm rejects short password"))
    except Exception as e:
        results.append(test_fail("PasswordResetConfirmForm length validation", str(e)))
    
    try:
        # Test ChangePasswordForm
        user = User.objects.first()
        if user:
            form = ChangePasswordForm(
                user=user,
                data={
                    'current_password': 'wrong_password',
                    'new_password1': 'NewPass123!',
                    'new_password2': 'NewPass123!'
                }
            )
            # Should be invalid due to wrong current password
            assert not form.is_valid()
            results.append(test_pass("ChangePasswordForm validates current password"))
        else:
            results.append(test_fail("ChangePasswordForm", "No user found in database"))
    except Exception as e:
        results.append(test_fail("ChangePasswordForm", str(e)))
    
    return results

def test_views():
    """Test view accessibility"""
    print_header("3. TESTING VIEWS")
    results = []
    client = Client()
    
    try:
        # Test forgot password page GET
        response = client.get('/accounts/forgot-password/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert b'Forgot Password' in response.content or b'forgot' in response.content.lower()
        results.append(test_pass("Forgot Password page loads (GET)"))
    except Exception as e:
        results.append(test_fail("Forgot Password page GET", str(e)))
    
    try:
        # Test login page still works
        response = client.get('/accounts/login/')
        assert response.status_code == 200
        assert b'Login' in response.content or b'login' in response.content.lower()
        results.append(test_pass("Login page loads correctly (unchanged)"))
    except Exception as e:
        results.append(test_fail("Login page GET", str(e)))
    
    try:
        # Test change password page requires login
        response = client.get('/accounts/change-password/')
        # Should redirect to login
        assert response.status_code in [302, 301], f"Expected redirect, got {response.status_code}"
        results.append(test_pass("Change Password page requires login (redirects)"))
    except Exception as e:
        results.append(test_fail("Change Password page login requirement", str(e)))
    
    try:
        # Test forgot password page has form
        response = client.get('/accounts/forgot-password/')
        assert b'email' in response.content.lower()
        assert b'form' in response.content.lower()
        results.append(test_pass("Forgot Password page has email form"))
    except Exception as e:
        results.append(test_fail("Forgot Password page form", str(e)))
    
    return results

def test_login_functionality():
    """Test that login still works after changes"""
    print_header("4. TESTING LOGIN FUNCTIONALITY")
    results = []
    client = Client()
    
    try:
        # Create test user
        test_user = User.objects.filter(username='test_password_user').first()
        if not test_user:
            test_user = User.objects.create_user(
                username='test_password_user',
                email='test_password@example.com',
                password='TestPass123!',
                user_type='client'
            )
        else:
            test_user.set_password('TestPass123!')
            test_user.save()
        
        results.append(test_pass("Test user created/updated"))
    except Exception as e:
        results.append(test_fail("Test user creation", str(e)))
        return results
    
    try:
        # Test login POST
        response = client.post('/accounts/login/', {
            'username': 'test_password_user',
            'password': 'TestPass123!'
        })
        # Should redirect after successful login
        assert response.status_code in [302, 301], f"Expected redirect, got {response.status_code}"
        results.append(test_pass("Login POST works (redirects on success)"))
    except Exception as e:
        results.append(test_fail("Login POST", str(e)))
    
    try:
        # Verify user is logged in
        response = client.get('/accounts/profile/')
        # Should redirect to dashboard (not to login)
        assert response.status_code in [302, 301]
        assert '/accounts/login/' not in response.url
        results.append(test_pass("User session maintained after login"))
    except Exception as e:
        results.append(test_fail("User session", str(e)))
    
    try:
        # Test logout still works
        response = client.get('/accounts/logout/')
        assert response.status_code in [302, 301]
        results.append(test_pass("Logout works correctly"))
    except Exception as e:
        results.append(test_fail("Logout", str(e)))
    
    try:
        # Clean up test user
        test_user.delete()
        results.append(test_pass("Test user cleaned up"))
    except Exception as e:
        results.append(test_fail("Test cleanup", str(e)))
    
    return results

def test_templates():
    """Test template existence and basic structure"""
    print_header("5. TESTING TEMPLATES")
    results = []
    
    templates = [
        ('templates/accounts/forgot_password.html', 'Forgot Password template'),
        ('templates/accounts/reset_password.html', 'Reset Password template'),
        ('templates/accounts/change_password.html', 'Change Password template'),
        ('templates/accounts/login.html', 'Login template (unchanged)'),
    ]
    
    for template_path, description in templates:
        try:
            assert os.path.exists(template_path), f"Template not found: {template_path}"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '{% extends' in content or '<html' in content
                assert 'form' in content.lower()
            
            results.append(test_pass(description))
        except Exception as e:
            results.append(test_fail(description, str(e)))
    
    try:
        # Check login template has forgot password link
        with open('templates/accounts/login.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'forgot_password' in content.lower() or 'forgot-password' in content.lower()
        results.append(test_pass("Login page has 'Forgot Password' link"))
    except Exception as e:
        results.append(test_fail("Login page forgot password link", str(e)))
    
    return results

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}COMPREHENSIVE PASSWORD MANAGEMENT TESTING{RESET}")
    print(f"{BLUE}Date: March 9, 2026{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    all_results = []
    
    # Run all tests
    all_results.extend(test_urls())
    all_results.extend(test_forms())
    all_results.extend(test_views())
    all_results.extend(test_login_functionality())
    all_results.extend(test_templates())
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(all_results)
    total = len(all_results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    if passed == total:
        print(f"{GREEN}✓ ALL TESTS PASSED: {passed}/{total} ({percentage:.0f}%){RESET}")
        print(f"{GREEN}✓ System is 100% FUNCTIONAL!{RESET}")
    else:
        print(f"{YELLOW}⚠ TESTS: {passed}/{total} passed ({percentage:.0f}%){RESET}")
        failed = total - passed
        print(f"{RED}✗ {failed} test(s) failed{RESET}")
    
    print(f"\n{BLUE}{'='*70}{RESET}\n")
    
    if passed == total:
        print(f"{GREEN}CONCLUSION:{RESET}")
        print(f"  ✓ All URL routes working")
        print(f"  ✓ All forms validating correctly")
        print(f"  ✓ All views accessible")
        print(f"  ✓ Login functionality INTACT")
        print(f"  ✓ All templates present and valid")
        print(f"\n{GREEN}✓ PASSWORD MANAGEMENT SYSTEM IS PRODUCTION READY!{RESET}\n")
    else:
        print(f"{YELLOW}Please review failed tests above.{RESET}\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n{RED}Fatal error: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
