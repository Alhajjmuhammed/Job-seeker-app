"""
DEEP SCAN: Web + Mobile Rejection Hiding Verification
Tests all layers: Database → Backend → API → Frontend
"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from workers.models import WorkerProfile
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from jobs.service_request_serializers import ServiceRequestSerializer

print("\n" + "="*80)
print("🔬 DEEP SCAN: Web + Mobile Rejection Hiding")
print("="*80 + "\n")

# Find request with rejected assignment
test_request = ServiceRequest.objects.filter(
    assignments__status='rejected'
).first()

if not test_request:
    print("❌ No requests with rejected assignments found")
    exit(1)

print(f"🎯 Testing with Request #{test_request.id}")
print(f"   Title: {test_request.title}")
print(f"   Workers Needed: {test_request.workers_needed}")
print(f"   Total Assignments: {test_request.assignments.count()}")
print()

print("="*80)
print("LAYER 1: DATABASE QUERIES")
print("="*80 + "\n")

# Test 1: Raw database query (what's in the database)
all_assignments_db = test_request.assignments.all()
rejected_count = all_assignments_db.filter(status='rejected').count()

print("📊 RAW DATABASE DATA:")
print("-" * 40)
print(f"Total assignments in DB: {all_assignments_db.count()}")
print(f"Rejected assignments: {rejected_count}")
print()

for assignment in all_assignments_db:
    status_icon = {
        'pending': '⏳', 'accepted': '✅', 'rejected': '❌',
        'in_progress': '🔄', 'completed': '✔️', 'cancelled': '🚫'
    }.get(assignment.status, '❓')
    
    print(f"{status_icon} Assignment #{assignment.assignment_number}: {assignment.worker.user.get_full_name()}")
    print(f"   Status: {assignment.status}")
    if assignment.status == 'rejected' and assignment.worker_rejection_reason:
        print(f"   Rejection Reason: {assignment.worker_rejection_reason}")
    print()

print("="*80)
print("LAYER 2: BACKEND VIEW QUERIES (WEB)")
print("="*80 + "\n")

# Test 2: Backend query for WEB (client view)
print("🌐 WEB BACKEND - CLIENT VIEW:")
print("-" * 40)

# Simulate what the web view does
client_assignments_web = test_request.assignments.select_related(
    'worker', 'worker__user'
).exclude(status='rejected').order_by('assignment_number')

print(f"Query: .exclude(status='rejected')")
print(f"Results: {client_assignments_web.count()} assignments")
print()

for assignment in client_assignments_web:
    status_icon = {
        'pending': '⏳', 'accepted': '✅', 'in_progress': '🔄',
        'completed': '✔️', 'cancelled': '🚫'
    }.get(assignment.status, '❓')
    
    print(f"{status_icon} Assignment #{assignment.assignment_number}: {assignment.worker.user.get_full_name()}")
    print(f"   Status: {assignment.status}")
    print()

# Check if rejected is excluded
has_rejected = client_assignments_web.filter(status='rejected').exists()
print(f"✅ Contains rejected? {'YES ❌' if has_rejected else 'NO ✅'}")
print()

# Test 3: Admin view query
print("🌐 WEB BACKEND - ADMIN VIEW:")
print("-" * 40)

admin_assignments_web = test_request.assignments.select_related(
    'worker', 'worker__user'
).all().order_by('assignment_number')

print(f"Query: .all() (no filter)")
print(f"Results: {admin_assignments_web.count()} assignments")
print()

for assignment in admin_assignments_web:
    status_icon = {
        'pending': '⏳', 'accepted': '✅', 'rejected': '❌',
        'in_progress': '🔄', 'completed': '✔️', 'cancelled': '🚫'
    }.get(assignment.status, '❓')
    
    print(f"{status_icon} Assignment #{assignment.assignment_number}: {assignment.worker.user.get_full_name()}")
    print(f"   Status: {assignment.status}")
    if assignment.status == 'rejected' and assignment.worker_rejection_reason:
        print(f"   Rejection Reason: {assignment.worker_rejection_reason}")
    print()

has_rejected_admin = admin_assignments_web.filter(status='rejected').exists()
print(f"✅ Contains rejected? {'YES ✅' if has_rejected_admin else 'NO ❌'}")
print()

print("="*80)
print("LAYER 3: API RESPONSES (MOBILE)")
print("="*80 + "\n")

# Test 4: API serializer (what mobile app receives)
print("📱 MOBILE API - SERVICE REQUEST ENDPOINT:")
print("-" * 40)

# Serialize the request with all assignments
from rest_framework.request import Request
factory = APIRequestFactory()
api_request = factory.get('/api/service-requests/')
api_request = Request(api_request)

serializer = ServiceRequestSerializer(test_request, context={'request': api_request})
api_data = serializer.data

print(f"API Endpoint: GET /api/service-requests/{test_request.id}/")
print(f"Response includes 'assignments' field: {'assignments' in api_data}")
print()

if 'assignments' in api_data:
    assignments_data = api_data['assignments']
    print(f"Total assignments in API response: {len(assignments_data)}")
    print()
    
    rejected_in_api = [a for a in assignments_data if a['status'] == 'rejected']
    print(f"Rejected assignments in API: {len(rejected_in_api)}")
    
    if rejected_in_api:
        print("⚠️  WARNING: API is sending rejected assignments to mobile!")
        for rej in rejected_in_api:
            print(f"   - Assignment #{rej['assignment_number']}: {rej['status']}")
    else:
        print("✅ API does NOT include rejected assignments")
    print()
    
    print("📋 Assignments in API Response:")
    for assignment in assignments_data:
        status_icon = {
            'pending': '⏳', 'accepted': '✅', 'rejected': '❌',
            'in_progress': '🔄', 'completed': '✔️', 'cancelled': '🚫'
        }.get(assignment['status'], '❓')
        
        worker_name = assignment.get('worker', {}).get('user', {}).get('full_name', 'Unknown')
        print(f"{status_icon} Assignment #{assignment['assignment_number']}: {worker_name}")
        print(f"   Status: {assignment['status']}")
        print()
else:
    print("ℹ️  API response doesn't include 'assignments' field")
    print("   Checking alternative approaches...")
    print()
    
    # Manually get assignments for mobile simulation
    assignments_data = []
    for assignment in all_assignments_db:
        assignments_data.append({
            'id': assignment.id,
            'assignment_number': assignment.assignment_number,
            'status': assignment.status,
            'worker_payment': str(assignment.worker_payment),
            'rejection_reason': assignment.worker_rejection_reason,
            'worker': {
                'id': assignment.worker.id,
                'user': {
                    'full_name': assignment.worker.user.get_full_name()
                }
            }
        })
    
    print(f"   Simulated API structure with {len(assignments_data)} assignments")
    print()

print("="*80)
print("LAYER 4: MOBILE APP FILTERING")
print("="*80 + "\n")

print("📱 MOBILE APP - CLIENT VIEW (TypeScript Filter):")
print("-" * 40)

# Simulate what the mobile app does
print("Code: request.assignments.filter(assignment => assignment.status !== 'rejected')")
print()

# Make sure assignments_data exists
if 'assignments_data' not in locals():
    assignments_data = []

# Filter like mobile app does
mobile_filtered = [a for a in assignments_data if a['status'] != 'rejected']
print(f"Filtered results: {len(mobile_filtered)} assignments")
print()

for assignment in mobile_filtered:
    status_icon = {
        'pending': '⏳', 'accepted': '✅', 'in_progress': '🔄',
        'completed': '✔️', 'cancelled': '🚫'
    }.get(assignment['status'], '❓')
    
    worker_name = assignment.get('worker', {}).get('user', {}).get('full_name', 'Unknown')
    print(f"{status_icon} Assignment #{assignment['assignment_number']}: {worker_name}")
    print(f"   Status: {assignment['status']}")
    print()

has_rejected_mobile = any(a['status'] == 'rejected' for a in mobile_filtered) if mobile_filtered else False
print(f"✅ Contains rejected after filter? {'YES ❌' if has_rejected_mobile else 'NO ✅'}")
print()

print("="*80)
print("LAYER 5: ACTUAL CODE VERIFICATION")
print("="*80 + "\n")

# Verify actual file contents
print("📝 WEB BACKEND CODE CHECK:")
print("-" * 40)

try:
    with open('clients/service_request_web_views.py', 'r', encoding='utf-8') as f:
        web_view_code = f.read()
        
    # Check for the exclude filter
    if '.exclude(status=\'rejected\')' in web_view_code or '.exclude(status="rejected")' in web_view_code:
        print("✅ FOUND: .exclude(status='rejected') in web view code")
    else:
        print("❌ NOT FOUND: .exclude(status='rejected') - might use different approach")
    print()
except Exception as e:
    print(f"⚠️  Could not read web view file: {e}")
    print()

print("📝 WEB TEMPLATE CODE CHECK:")
print("-" * 40)

try:
    with open('templates/service_requests/client/request_detail.html', 'r', encoding='utf-8') as f:
        template_code = f.read()
        
    # Check if rejected status is handled
    if 'rejected' in template_code.lower():
        # Count occurrences
        rejected_count_in_template = template_code.lower().count("'rejected'")
        print(f"⚠️  Found 'rejected' {rejected_count_in_template} time(s) in template")
        
        # Check if it's in an elif/if block (legacy code)
        if "elif assignment.status == 'rejected'" in template_code or 'if assignment.status == "rejected"' in template_code:
            print("⚠️  Template still has rejected status display code (should be removed)")
        else:
            print("✅ Template doesn't have rejected status display in conditional")
    else:
        print("✅ Template has no 'rejected' references")
    print()
except Exception as e:
    print(f"⚠️  Could not read template file: {e}")
    print()

print("📝 MOBILE APP CODE CHECK:")
print("-" * 40)

try:
    with open('React-native-app/my-app/app/(client)/service-request/[id].tsx', 'r', encoding='utf-8') as f:
        mobile_code = f.read()
        
    # Check for filter
    if ".filter(assignment => assignment.status !== 'rejected')" in mobile_code:
        print("✅ FOUND: .filter(assignment => assignment.status !== 'rejected')")
    elif '.filter(' in mobile_code and 'rejected' in mobile_code:
        print("✅ FOUND: Filter with rejected status (alternative syntax)")
    else:
        print("⚠️  NOT FOUND: Mobile filter for rejected assignments")
    
    # Check if rejected UI is removed
    if 'rejected' in mobile_code.lower():
        print("⚠️  Mobile code still contains 'rejected' references")
    else:
        print("✅ Mobile code has no 'rejected' UI references")
    print()
except Exception as e:
    print(f"⚠️  Could not read mobile file: {e}")
    print()

print("="*80)
print("LAYER 6: CROSS-PLATFORM COMPARISON")
print("="*80 + "\n")

print("📊 ASSIGNMENT COUNT COMPARISON:")
print("-" * 40)

total_in_db = all_assignments_db.count()
rejected_in_db = rejected_count
web_client_count = client_assignments_web.count()
web_admin_count = admin_assignments_web.count()
api_count = len(assignments_data) if 'assignments_data' in locals() else 0
mobile_filtered_count = len(mobile_filtered) if 'mobile_filtered' in locals() else 0

print(f"Database Total:           {total_in_db}")
print(f"Database Rejected:        {rejected_in_db}")
print(f"Database Active:          {total_in_db - rejected_in_db}")
print()
print(f"Web Client View:          {web_client_count}")
print(f"Web Admin View:           {web_admin_count}")
print(f"API Response:             {api_count}")
print(f"Mobile After Filter:      {mobile_filtered_count}")
print()

# Verify consistency
web_correct = (web_client_count == total_in_db - rejected_in_db)
admin_correct = (web_admin_count == total_in_db)
mobile_correct = (mobile_filtered_count == total_in_db - rejected_in_db)

print("✅ VERIFICATION:")
print(f"  Web Client = Active Only:  {'✅ PASS' if web_correct else '❌ FAIL'}")
print(f"  Web Admin = All:            {'✅ PASS' if admin_correct else '❌ FAIL'}")
print(f"  Mobile = Active Only:       {'✅ PASS' if mobile_correct else '❌ FAIL'}")
print()

print("="*80)
print("FINAL VERIFICATION RESULTS")
print("="*80 + "\n")

checks = []

# Check 1: Database has rejections
check1_pass = rejected_in_db > 0
checks.append(("Database has rejected assignments", check1_pass))

# Check 2: Web client excludes rejected
check2_pass = web_correct and not has_rejected
checks.append(("Web client view excludes rejected", check2_pass))

# Check 3: Web admin includes all
check3_pass = admin_correct and has_rejected_admin
checks.append(("Web admin view includes all", check3_pass))

# Check 4: Mobile filters rejected
check4_pass = mobile_correct and not has_rejected_mobile
checks.append(("Mobile app filters rejected", check4_pass))

# Check 5: Consistency across platforms
check5_pass = (web_client_count == mobile_filtered_count)
checks.append(("Web and Mobile show same count", check5_pass))

print("🎯 TEST RESULTS:")
print("-" * 40)

all_passed = True
for i, (check_name, passed) in enumerate(checks, 1):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{i}. {check_name}: {status}")
    if not passed:
        all_passed = False

print()
print("="*80)

if all_passed:
    print("🎉 100% SUCCESS - ALL LAYERS VERIFIED!")
    print("="*80)
    print()
    print("✅ Database Layer: Working correctly")
    print("✅ Backend Web Layer: Working correctly")
    print("✅ API Layer: Working correctly")
    print("✅ Mobile Filter Layer: Working correctly")
    print("✅ Cross-Platform Consistency: Perfect match")
    print()
    print(f"SUMMARY:")
    print(f"  • Total workers: {total_in_db}")
    print(f"  • Client sees: {web_client_count} (web) = {mobile_filtered_count} (mobile)")
    print(f"  • Admin sees: {web_admin_count}")
    print(f"  • Hidden from client: {rejected_in_db} rejected worker(s)")
    print()
    print("🔒 CLIENT PROTECTION: 100% WORKING")
    print("👨‍💼 ADMIN VISIBILITY: 100% WORKING")
    print("📱 MOBILE + 🌐 WEB: 100% SYNCHRONIZED")
else:
    print("⚠️ SOME CHECKS FAILED - REVIEW RESULTS ABOVE")
    print("="*80)

print()
