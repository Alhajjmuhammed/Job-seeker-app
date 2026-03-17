#!/usr/bin/env python3
"""
Test Worker Display in My Requests Page
Verify that assigned workers show correctly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from workers.models import WorkerProfile
from accounts.models import User
from django.db import models as django_models

print("=" * 80)
print("WORKER DISPLAY VERIFICATION TEST")
print("=" * 80)
print()

# Get test data
service_requests = ServiceRequest.objects.all()[:5]

print(f"📋 Checking first 5 service requests...\n")

for sr in service_requests:
    print(f"Service Request #{sr.id}: {sr.title}")
    print(f"  Status: {sr.status}")
    print(f"  Client: {sr.client.get_full_name()}")
    
    # Check legacy assigned_worker field
    if sr.assigned_worker:
        print(f"  ✅ Legacy assigned_worker: {sr.assigned_worker.user.get_full_name()}")
        print(f"     Worker accepted: {sr.worker_accepted}")
    else:
        print(f"  ❌ Legacy assigned_worker: None")
    
    # Check new assignments relationship
    assignments = sr.assignments.all()
    if assignments.exists():
        print(f"  ✅ New assignments system: {assignments.count()} assignment(s)")
        for assignment in assignments:
            print(f"     - Worker: {assignment.worker.user.get_full_name()}")
            print(f"       Status: {assignment.status}")
            print(f"       Worker accepted: {assignment.worker_accepted}")
            print(f"       Assignment #: {assignment.assignment_number}")
    else:
        print(f"  ❌ New assignments system: No assignments")
    
    # What should be displayed in the Worker column?
    print(f"\n  📊 WORKER COLUMN SHOULD SHOW:")
    
    accepted_assignments = assignments.filter(worker_accepted=True)
    pending_assignments = assignments.filter(status='pending')
    
    if accepted_assignments.exists():
        print(f"     ✅ {accepted_assignments.count()} accepted worker(s):")
        for assignment in accepted_assignments:
            print(f"        - {assignment.worker.user.get_full_name()} (Worker #{assignment.assignment_number})")
    elif pending_assignments.exists():
        print(f"     ⏳ {pending_assignments.count()} pending worker(s):")
        for assignment in pending_assignments:
            print(f"        - {assignment.worker.user.get_full_name()} (Awaiting Response)")
    elif sr.assigned_worker:
        if sr.worker_accepted:
            print(f"     ✅ (Legacy) {sr.assigned_worker.user.get_full_name()} (Accepted)")
        else:
            print(f"     ⏳ (Legacy) {sr.assigned_worker.user.get_full_name()} (Awaiting Response)")
    else:
        print(f"     ❌ Not assigned")
    
    print()
    print("-" * 80)
    print()

# Summary
print("\n" + "=" * 80)
print("SUMMARY - DATA CHECK")
print("=" * 80)
print()

total_requests = ServiceRequest.objects.count()
requests_with_legacy_worker = ServiceRequest.objects.filter(assigned_worker__isnull=False).count()
requests_with_assignments = ServiceRequest.objects.filter(assignments__isnull=False).distinct().count()
requests_with_accepted_workers = ServiceRequest.objects.filter(
    assignments__worker_accepted=True
).distinct().count()

print(f"Total service requests: {total_requests}")
print(f"Requests with legacy assigned_worker: {requests_with_legacy_worker}")
print(f"Requests with new assignments: {requests_with_assignments}")
print(f"Requests with accepted workers: {requests_with_accepted_workers}")
print()

# Check for problematic cases
print("=" * 80)
print("CHECKING FOR ISSUES")
print("=" * 80)
print()

# Case 1: Status is 'assigned' but no worker in either system
assigned_no_worker = ServiceRequest.objects.filter(
    status='assigned',
    assigned_worker__isnull=True
).exclude(
    assignments__isnull=False
)

if assigned_no_worker.exists():
    print(f"⚠️  ISSUE: {assigned_no_worker.count()} request(s) with status='assigned' but no worker:")
    for sr in assigned_no_worker[:3]:
        print(f"   - Request #{sr.id}: {sr.title}")
else:
    print("✅ No requests with status='assigned' but missing worker")

print()

# Case 2: Has worker but status is still 'pending'
pending_with_worker = ServiceRequest.objects.filter(
    status='pending'
).filter(
    django_models.Q(assigned_worker__isnull=False) | 
    django_models.Q(assignments__isnull=False)
).distinct()

if pending_with_worker.exists():
    print(f"⚠️  INFO: {pending_with_worker.count()} request(s) with status='pending' but has worker assigned:")
    for sr in pending_with_worker[:3]:
        print(f"   - Request #{sr.id}: {sr.title}")
        assignments = sr.assignments.all()
        if assignments.exists():
            for assignment in assignments:
                print(f"     Assignment status: {assignment.status}, Accepted: {assignment.worker_accepted}")
else:
    print("✅ No requests with status='pending' but has assigned worker")

print()

# Case 3: Worker accepted but status not updated
from django.db import models as django_models
accepted_but_wrong_status = ServiceRequest.objects.filter(
    django_models.Q(worker_accepted=True) | 
    django_models.Q(assignments__worker_accepted=True)
).exclude(
    status__in=['in_progress', 'completed']
).distinct()

if accepted_but_wrong_status.exists():
    print(f"⚠️  ISSUE: {accepted_but_wrong_status.count()} request(s) where worker accepted but status not updated:")
    for sr in accepted_but_wrong_status[:3]:
        print(f"   - Request #{sr.id}: {sr.title} (Status: {sr.status})")
else:
    print("✅ No requests with worker accepted but wrong status")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print()
print("✅ The fix has been applied to:")
print("   1. View: Added prefetch_related('assignments__worker__user')")
print("   2. Template: Updated to check assignments first, then legacy field")
print()
print("🔄 To see the changes:")
print("   1. Refresh the page: http://127.0.0.1:8080/services/client/my-requests/")
print("   2. Workers who have ACCEPTED should show with green checkmark")
print("   3. Workers who are PENDING should show with hourglass icon")
print("   4. Unassigned requests should show 'Not assigned'")
print()
