#!/usr/bin/env python
"""
Verification script to confirm availability checking is implemented
in ALL client service request entry points.

Date: March 16, 2026
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

print("=" * 80)
print("AVAILABILITY CHECKING VERIFICATION - ALL ENTRY POINTS")
print("=" * 80)
print()

# Define all entry points where clients can create service requests
entry_points = {
    "Web Entry Points": [
        {
            "name": "Main Request Service (NEW)",
            "url": "/services/client/request-service/",
            "view_function": "clients.service_request_web_views.client_web_request_service",
            "file": "clients/service_request_web_views.py",
        },
        {
            "name": "Legacy Request Service",
            "url": "/clients/services/<category_id>/request/",
            "view_function": "clients.views.request_service",
            "file": "clients/views.py",
        }
    ],
    "Mobile API Entry Points": [
        {
            "name": "Mobile Request Service API",
            "endpoint": "POST /api/clients/request-service/",
            "view_function": "clients.api_views.request_service",
            "file": "clients/api_views.py",
        }
    ]
}

print("🔍 Checking all entry points for availability checking...")
print()

# Check each file for availability checking implementation
import re

def check_availability_logic(file_path, function_name):
    """Check if a file contains availability checking logic"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for availability checking patterns
        patterns = [
            r"available_workers\s*=.*WorkerProfile\.objects\.filter",
            r"availability\s*==?\s*['\"]available['\"]",
            r"service_assignments__status__in",
            r"\.exclude\(.*service_assignments",
        ]
        
        has_checking = all(re.search(pattern, content, re.IGNORECASE | re.DOTALL) 
                          for pattern in patterns[:2])  # At least basic availability check
        
        has_active_check = any(re.search(pattern, content, re.IGNORECASE | re.DOTALL) 
                              for pattern in patterns[2:])  # Active assignment exclusion
        
        return has_checking, has_active_check
    except Exception as e:
        return False, False

results = []

for category, endpoints in entry_points.items():
    print(f"\n📍 {category}:")
    print("-" * 80)
    
    for endpoint in endpoints:
        file_path = endpoint['file']
        has_basic, has_active = check_availability_logic(file_path, 
                                                          endpoint.get('view_function', ''))
        
        status = "✅ IMPLEMENTED" if (has_basic and has_active) else "❌ MISSING"
        
        print(f"\n  {endpoint['name']}")
        print(f"  File: {file_path}")
        print(f"  URL/Endpoint: {endpoint.get('url') or endpoint.get('endpoint')}")
        print(f"  Basic Availability Check: {'✅' if has_basic else '❌'}")
        print(f"  Active Assignment Exclusion: {'✅' if has_active else '❌'}")
        print(f"  Overall Status: {status}")
        
        results.append({
            'name': endpoint['name'],
            'status': 'PASS' if (has_basic and has_active) else 'FAIL',
            'basic': has_basic,
            'active': has_active
        })

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r['status'] == 'PASS')
total = len(results)

print(f"\nTotal Entry Points Checked: {total}")
print(f"With Complete Availability Checking: {passed}")
print(f"Missing Availability Checking: {total - passed}")

if passed == total:
    print("\n✅ SUCCESS: All entry points have availability checking implemented!")
else:
    print(f"\n⚠️ WARNING: {total - passed} entry point(s) missing availability checking")
    print("\nMissing from:")
    for r in results:
        if r['status'] == 'FAIL':
            print(f"  - {r['name']}")
            if not r['basic']:
                print("    Missing: Basic availability check")
            if not r['active']:
                print("    Missing: Active assignment exclusion")

print("\n" + "=" * 80)
print()

# Additional verification - check if all three locations have the same logic
print("🔄 Verifying consistency across implementations...")
print()

files_to_check = [
    "clients/service_request_web_views.py",
    "clients/views.py",
    "clients/api_views.py"
]

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count occurrences of key availability checking components
        count_available = content.count("availability='available'")
        count_verified = content.count("verification_status='verified'")
        count_exclude = content.count("service_assignments__status__in")
        
        print(f"📄 {file_path}")
        print(f"   - Checks for 'available' status: {count_available}")
        print(f"   - Checks for 'verified' status: {count_verified}")
        print(f"   - Excludes active assignments: {count_exclude}")
        print()
    except:
        pass

print("=" * 80)
print("Verification complete!")
print("=" * 80)
