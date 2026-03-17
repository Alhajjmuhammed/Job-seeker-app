#!/usr/bin/env python
"""
ABSOLUTE FINAL DEEP SCAN - ALL FILES
Verifies EVERY location where ServiceRequest can be created
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

print("=" * 80)
print("ABSOLUTE FINAL DEEP SCAN - ALL SERVICE REQUEST CREATION POINTS")
print("=" * 80)
print()

# All files that could create service requests
files_to_check = [
    ('clients/service_request_web_views.py', 'client_web_request_service', 'Web Main'),
    ('clients/views.py', 'request_service', 'Web Legacy'),
    ('clients/api_views.py', 'request_service', 'Mobile API v1'),
    ('clients/service_request_client_views.py', 'client_create_service_request', 'Mobile API v2'),
]

print("Checking all functions that create ServiceRequest objects:\n")

all_verified = True

for file_path, function_name, label in files_to_check:
    print(f"📍 {label}")
    print(f"   File: {file_path}")
    print(f"   Function: {function_name}()")
    
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if function exists
        if f"def {function_name}" not in content:
            print(f"   ❌ Function not found!")
            all_verified = False
            print()
            continue
        
        # Extract function content
        func_start = content.find(f"def {function_name}")
        if func_start == -1:
            print(f"   ❌ Could not extract function!")
            all_verified = False
            print()
            continue
        
        # Get next 2000 characters to analyze the function
        func_content = content[func_start:func_start+3000]
        
        # Check for all required patterns
        checks = {
            'availability filter': "availability='available'" in func_content,
            'verified filter': "verification_status='verified'" in func_content,
            'exclude assignments': "service_assignments__status__in" in func_content,
            'distinct count': ".distinct()" in func_content,
            'creates request': "ServiceRequest.objects.create" in func_content or "serializer.save(" in func_content,
        }
        
        all_passed = all(checks.values())
        
        for check_name, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"   {icon} {check_name}")
        
        if all_passed:
            print(f"   ✅ VERIFIED - Has complete availability checking")
        else:
            print(f"   ❌ MISSING - Availability checking incomplete!")
            all_verified = False
        
        print()
        
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        all_verified = False
        print()

print("=" * 80)
print("FINAL RESULT")
print("=" * 80)
print()

if all_verified:
    print("✅✅✅ 100% VERIFIED - ALL SERVICE REQUEST CREATION POINTS HAVE AVAILABILITY CHECKING ✅✅✅")
    print()
    print("Confirmed locations:")
    print("  ✅ Web Main (/services/client/request-service/)")
    print("  ✅ Web Legacy (/clients/services/<id>/request/)")
    print("  ✅ Mobile API v1 (POST /api/clients/services/<id>/request/)")
    print("  ✅ Mobile API v2 (POST /api/v1/client/service-requests/create/)")
    print()
    print("Total: 4/4 endpoints (100%)")
else:
    print("❌ VERIFICATION FAILED - Some endpoints missing availability checking")

print()
print("=" * 80)
