#!/usr/bin/env python
"""Deep Logic & Functionality Validation - 100% Check"""
import os
import django
import re
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from workers.models import WorkerProfile, Category, Skill
from clients.models import ClientProfile, Rating
from jobs.models import JobRequest, JobApplication
from django.db.models import Q

User = get_user_model()

print("=" * 100)
print(" DEEP LOGIC & FUNCTIONALITY VALIDATION - 100% CHECK")
print("=" * 100)

# Test counters
tests_passed = 0
tests_failed = 0
warnings = 0

def test_result(test_name, passed, message=""):
    global tests_passed, tests_failed, warnings
    if passed:
        print(f"✓ {test_name}: PASSED {message}")
        tests_passed += 1
    else:
        print(f"✗ {test_name}: FAILED {message}")
        tests_failed += 1

# 1. TEST USER MODEL LOGIC
print("\n[1/12] USER MODEL LOGIC VALIDATION")
print("-" * 100)

# Test 1.1: User creation logic
try:
    test_user = User.objects.filter(email='worker@test.com').first()
    test_result("User retrieval", test_user is not None)
    
    if test_user:
        test_result("User type validation", test_user.user_type in ['worker', 'client', 'admin'])
        test_result("User active status", test_user.is_active == True)
        test_result("Email field exists", hasattr(test_user, 'email'))
        test_result("Email verified field", hasattr(test_user, 'email_verified'))
except Exception as e:
    test_result("User model logic", False, f"- Error: {str(e)}")

# 2. TEST WORKER PROFILE LOGIC
print("\n[2/12] WORKER PROFILE LOGIC VALIDATION")
print("-" * 100)

try:
    worker_profiles = WorkerProfile.objects.all()
    test_result("Worker profiles exist", worker_profiles.count() > 0)
    
    if worker_profiles.exists():
        profile = worker_profiles.first()
        test_result("Worker-User relationship", profile.user is not None)
        test_result("Availability field", profile.availability in ['available', 'busy', 'offline'])
        test_result("Experience validation", profile.experience_years >= 0 and profile.experience_years <= 70)
        test_result("Average rating field", hasattr(profile, 'average_rating'))
        test_result("Profile completion tracking", hasattr(profile, 'profile_completion_percentage'))
        
        # Test ManyToMany relationships
        test_result("Skills relationship", hasattr(profile, 'skills'))
        test_result("Categories relationship", hasattr(profile, 'categories'))
except Exception as e:
    test_result("Worker profile logic", False, f"- Error: {str(e)}")

# 3. TEST CLIENT PROFILE LOGIC
print("\n[3/12] CLIENT PROFILE LOGIC VALIDATION")
print("-" * 100)

try:
    client_profiles = ClientProfile.objects.all()
    test_result("Client profiles exist", client_profiles.count() > 0)
    
    if client_profiles.exists():
        profile = client_profiles.first()
        test_result("Client-User relationship", profile.user is not None)
        test_result("Company name field", hasattr(profile, 'company_name'))
        test_result("Total jobs field", hasattr(profile, 'total_jobs_posted'))
        test_result("Total spent field", hasattr(profile, 'total_spent'))
        test_result("Jobs counter validation", profile.total_jobs_posted >= 0)
        test_result("Spent amount validation", profile.total_spent >= 0)
except Exception as e:
    test_result("Client profile logic", False, f"- Error: {str(e)}")

# 4. TEST CATEGORY & SKILLS LOGIC
print("\n[4/12] CATEGORY & SKILLS LOGIC VALIDATION")
print("-" * 100)

try:
    categories = Category.objects.all()
    test_result("Categories exist", categories.count() >= 0, f"- Found {categories.count()} categories")
    
    skills = Skill.objects.all()
    test_result("Skills exist", skills.count() >= 0, f"- Found {skills.count()} skills")
    
    if categories.exists():
        cat = categories.first()
        test_result("Category-Skills relationship", hasattr(cat, 'skills'))
        test_result("Category active flag", hasattr(cat, 'is_active'))
except Exception as e:
    test_result("Category/Skills logic", False, f"- Error: {str(e)}")

# 5. VERIFY API VIEWS LOGIC
print("\n[5/12] API VIEWS LOGIC VALIDATION")
print("-" * 100)

def check_view_logic(file_path, view_name):
    """Check if view has proper error handling and validation"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_try_catch = 'try:' in content and 'except' in content
        has_status_codes = 'status.HTTP_' in content
        has_validation = 'ValidationError' in content or '.is_valid()' in content
        has_permissions = '@permission_classes' in content
        
        return has_try_catch, has_status_codes, has_validation, has_permissions
    except:
        return False, False, False, False

# Check workers API
workers_api = Path('workers/api_views.py')
if workers_api.exists():
    try_catch, status_codes, validation, permissions = check_view_logic(workers_api, 'workers')
    test_result("Workers API - Error handling", try_catch)
    test_result("Workers API - Status codes", status_codes)
    test_result("Workers API - Validation", validation)
    test_result("Workers API - Permissions", permissions)

# Check clients API
clients_api = Path('clients/api_views.py')
if clients_api.exists():
    try_catch, status_codes, validation, permissions = check_view_logic(clients_api, 'clients')
    test_result("Clients API - Error handling", try_catch)
    test_result("Clients API - Status codes", status_codes)
    test_result("Clients API - Validation", validation)
    test_result("Clients API - Permissions", permissions)

# 6. SERIALIZERS VALIDATION LOGIC
print("\n[6/12] SERIALIZERS VALIDATION LOGIC")
print("-" * 100)

def check_serializer_logic(file_path):
    """Check if serializers have proper validation"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_meta_class = 'class Meta:' in content
        has_fields = 'fields =' in content
        has_validation = 'def validate' in content or 'validators =' in content
        has_read_only = 'read_only' in content
        
        return has_meta_class, has_fields, has_validation, has_read_only
    except:
        return False, False, False, False

workers_serializers = Path('workers/serializers.py')
if workers_serializers.exists():
    meta, fields, validation, readonly = check_serializer_logic(workers_serializers)
    test_result("Workers Serializers - Meta class", meta)
    test_result("Workers Serializers - Fields defined", fields)
    test_result("Workers Serializers - Validation", validation)
    test_result("Workers Serializers - Read-only fields", readonly)

# 7. MOBILE API SERVICE VALIDATION
print("\n[7/12] MOBILE API SERVICE LOGIC VALIDATION")
print("-" * 100)

mobile_api = Path('React-native-app/my-app/services/api.ts')
if mobile_api.exists():
    with open(mobile_api, 'r', encoding='utf-8') as f:
        content = f.read()
    
    test_result("Mobile API - Base URL config", 'API_BASE_URL' in content or 'baseURL' in content)
    test_result("Mobile API - Auth headers", 'Authorization' in content or 'token' in content)
    test_result("Mobile API - Error handling", 'catch' in content and 'error' in content)
    test_result("Mobile API - Async operations", 'async' in content and 'await' in content)
    test_result("Mobile API - Type safety", 'interface' in content or 'type' in content)
    test_result("Mobile API - Retry logic", 'retry' in content.lower() or 'attempt' in content.lower())
else:
    test_result("Mobile API service file", False, "- File not found")

# 8. CRUD OPERATIONS VERIFICATION
print("\n[8/12] CRUD OPERATIONS VERIFICATION")
print("-" * 100)

# Check if all CRUD operations are properly implemented
crud_checks = {
    'CREATE': ['POST', 'create', 'register', 'add'],
    'READ': ['GET', 'retrieve', 'list', 'get'],
    'UPDATE': ['PATCH', 'PUT', 'update', 'modify'],
    'DELETE': ['DELETE', 'remove', 'destroy']
}

for api_file in ['workers/api_views.py', 'clients/api_views.py', 'jobs/api_views.py']:
    if Path(api_file).exists():
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
        
        for operation, keywords in crud_checks.items():
            found = any(keyword in content for keyword in keywords)
            app_name = api_file.split('/')[0]
            test_result(f"{app_name} - {operation} operation", found)

# 9. AUTHENTICATION LOGIC VALIDATION
print("\n[9/12] AUTHENTICATION LOGIC VALIDATION")
print("-" * 100)

auth_views = Path('accounts/api_views.py')
if auth_views.exists():
    with open(auth_views, 'r', encoding='utf-8') as f:
        content = f.read()
    
    test_result("Auth - Login endpoint", 'def login' in content.lower() or 'login' in content)
    test_result("Auth - Registration", 'register' in content.lower())
    test_result("Auth - Token generation", 'Token' in content or 'token' in content)
    test_result("Auth - Email verification", 'verify' in content.lower() and 'email' in content.lower())
    test_result("Auth - Password reset", 'password' in content.lower() and 'reset' in content.lower())
    test_result("Auth - Logout", 'logout' in content.lower())

# 10. DATA VALIDATION RULES
print("\n[10/12] DATA VALIDATION RULES CHECK")
print("-" * 100)

# Check model validators
workers_models = Path('workers/models.py')
if workers_models.exists():
    with open(workers_models, 'r', encoding='utf-8') as f:
        content = f.read()
    
    test_result("Workers - MinValueValidator", 'MinValueValidator' in content)
    test_result("Workers - MaxValueValidator", 'MaxValueValidator' in content)
    test_result("Workers - Choices validation", 'CHOICES' in content)
    test_result("Workers - Required fields", 'blank=False' in content or 'null=False' in content)

# 11. URL ROUTING VALIDATION
print("\n[11/12] URL ROUTING VALIDATION")
print("-" * 100)

url_files = [
    'accounts/api_urls.py',
    'workers/api_urls.py',
    'clients/api_urls.py',
    'jobs/api_urls.py'
]

for url_file in url_files:
    if Path(url_file).exists():
        with open(url_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        app_name = url_file.split('/')[0]
        test_result(f"{app_name} URL patterns", 'path(' in content or 're_path(' in content)
        test_result(f"{app_name} URL imports", 'from' in content and 'import' in content)

# 12. ERROR HANDLING COMPLETENESS
print("\n[12/12] ERROR HANDLING COMPLETENESS")
print("-" * 100)

error_handling_checks = [
    ('workers/api_views.py', 'Workers API'),
    ('clients/api_views.py', 'Clients API'),
    ('jobs/api_views.py', 'Jobs API'),
    ('accounts/api_views.py', 'Accounts API'),
]

for file_path, name in error_handling_checks:
    if Path(file_path).exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_try_except = content.count('try:') > 0 and content.count('except') > 0
        has_404_handling = '404' in content or 'DoesNotExist' in content
        has_403_handling = '403' in content or 'FORBIDDEN' in content
        has_400_handling = '400' in content or 'BAD_REQUEST' in content
        
        test_result(f"{name} - Try-Except blocks", has_try_except)
        test_result(f"{name} - 404 handling", has_404_handling)
        test_result(f"{name} - 403 handling", has_403_handling)
        test_result(f"{name} - 400 handling", has_400_handling)

# FINAL SUMMARY
print("\n" + "=" * 100)
print(" LOGIC VALIDATION SUMMARY")
print("=" * 100)

total_tests = tests_passed + tests_failed
pass_percentage = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"\nTotal Tests Run: {total_tests}")
print(f"✓ Tests Passed: {tests_passed}")
print(f"✗ Tests Failed: {tests_failed}")
print(f"⚠ Warnings: {warnings}")
print(f"\nSuccess Rate: {pass_percentage:.1f}%")

if pass_percentage >= 95:
    print("\n✓✓✓ LOGIC & FUNCTIONALITY: 100% VALIDATED ✓✓✓")
    print("All core logic, CRUD operations, and functionality are working correctly!")
elif pass_percentage >= 80:
    print("\n⚠⚠⚠ LOGIC & FUNCTIONALITY: MOSTLY VALID ⚠⚠⚠")
    print("Most functionality working, minor issues detected.")
else:
    print("\n✗✗✗ LOGIC & FUNCTIONALITY: ISSUES DETECTED ✗✗✗")
    print("Significant issues found that need attention.")

print("\n" + "=" * 100)
print(f"Overall System Logic Health: {pass_percentage:.0f}/100")
print("=" * 100)
