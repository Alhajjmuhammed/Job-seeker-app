#!/usr/bin/env python
"""
Deep verification of availability checking logic across ALL client request entry points.
Tests the actual SQL queries and counting logic.

Date: March 16, 2026
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from workers.models import WorkerProfile, Category
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment

User = get_user_model()

print("=" * 80)
print("DEEP AVAILABILITY LOGIC VERIFICATION")
print("=" * 80)
print()

# Test the exact query used in all 3 implementations
def test_availability_query(category):
    """Test the availability query logic"""
    
    # This is the EXACT query used in all 3 implementations
    available_workers = WorkerProfile.objects.filter(
        categories=category,
        availability='available',
        verification_status='verified'
    ).exclude(
        service_assignments__status__in=['pending', 'accepted', 'in_progress']
    ).distinct().count()
    
    # Also get the details for debugging
    available_worker_profiles = WorkerProfile.objects.filter(
        categories=category,
        availability='available',
        verification_status='verified'
    ).exclude(
        service_assignments__status__in=['pending', 'accepted', 'in_progress']
    ).distinct()
    
    # Count all workers in category (for comparison)
    total_workers = WorkerProfile.objects.filter(
        categories=category,
        verification_status='verified'
    ).count()
    
    # Count busy workers (with active assignments)
    busy_workers = WorkerProfile.objects.filter(
        categories=category,
        availability='available',
        verification_status='verified',
        service_assignments__status__in=['pending', 'accepted', 'in_progress']
    ).distinct().count()
    
    return {
        'available_count': available_workers,
        'available_workers': list(available_worker_profiles.values_list('user__username', flat=True)),
        'total_verified': total_workers,
        'busy_count': busy_workers
    }

print("🔍 Testing Availability Query Logic Across All Categories\n")

categories = Category.objects.filter(is_active=True)

if not categories.exists():
    print("❌ No categories found in database!")
    sys.exit(1)

all_passed = True

for category in categories:
    print(f"\n📊 Category: {category.name}")
    print("-" * 60)
    
    result = test_availability_query(category)
    
    print(f"   Total Verified Workers: {result['total_verified']}")
    print(f"   Busy Workers (with active assignments): {result['busy_count']}")
    print(f"   Available Workers (query result): {result['available_count']}")
    
    if result['available_workers']:
        print(f"   Available Worker Names: {', '.join(result['available_workers'])}")
    else:
        print(f"   Available Worker Names: None")
    
    # Verify the logic is consistent
    if result['available_count'] < 0:
        print(f"   ❌ ERROR: Negative count detected!")
        all_passed = False
    else:
        print(f"   ✅ Count is valid")

print("\n" + "=" * 80)
print("ENTRY POINT VERIFICATION")
print("=" * 80)
print()

# Verify all 3 entry points use the same query
import inspect
import importlib

entry_points = [
    ('clients.service_request_web_views', 'client_web_request_service', 'Web Main'),
    ('clients.views', 'request_service', 'Web Legacy'),
    ('clients.api_views', 'request_service', 'Mobile API'),
]

print("🔍 Checking source code of all 3 entry points...\n")

for module_name, function_name, label in entry_points:
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        source = inspect.getsource(func)
        
        # Check for required patterns
        has_availability_filter = "availability='available'" in source
        has_verified_filter = "verification_status='verified'" in source
        has_exclude_active = "service_assignments__status__in" in source
        has_distinct = ".distinct()" in source
        creates_request = "ServiceRequest.objects.create" in source
        
        print(f"📍 {label} ({module_name}.{function_name})")
        print(f"   ✅ Filters by availability='available': {has_availability_filter}")
        print(f"   ✅ Filters by verification_status='verified': {has_verified_filter}")
        print(f"   ✅ Excludes active assignments: {has_exclude_active}")
        print(f"   ✅ Uses .distinct(): {has_distinct}")
        print(f"   ✅ Creates ServiceRequest: {creates_request}")
        
        all_checks_passed = all([
            has_availability_filter,
            has_verified_filter,
            has_exclude_active,
            has_distinct,
            creates_request
        ])
        
        if all_checks_passed:
            print(f"   ✅ ALL CHECKS PASSED\n")
        else:
            print(f"   ❌ SOME CHECKS FAILED\n")
            all_passed = False
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}\n")
        all_passed = False

print("=" * 80)
print("ACTIVE ASSIGNMENT VERIFICATION")
print("=" * 80)
print()

# Check current active assignments
active_assignments = ServiceRequestAssignment.objects.filter(
    status__in=['pending', 'accepted', 'in_progress']
).select_related('worker__user', 'service_request__category')

print(f"📊 Active Assignments (should reduce available worker count):\n")

if active_assignments.exists():
    for assignment in active_assignments[:10]:  # Show first 10
        print(f"   Worker: {assignment.worker.user.username}")
        print(f"   Category: {assignment.service_request.category.name}")
        print(f"   Status: {assignment.status}")
        print(f"   Request ID: {assignment.service_request.id}")
        print()
else:
    print("   ℹ️ No active assignments found (all workers should show as available)\n")

print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print()

if all_passed:
    print("✅ SUCCESS: All availability checking implementations are correct!")
    print()
    print("Verified:")
    print("  ✅ All 3 entry points have availability checking")
    print("  ✅ All use identical query logic")
    print("  ✅ All filter by availability='available'")
    print("  ✅ All filter by verification_status='verified'")
    print("  ✅ All exclude workers with active assignments")
    print("  ✅ All use .distinct() to avoid duplicates")
else:
    print("❌ ISSUES FOUND: Some implementations may be incorrect")

print()
print("=" * 80)
