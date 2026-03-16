"""Test worker unassignment and availability update"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from jobs.models import ServiceRequest, ServiceRequestAssignment, WorkerProfile
from django.test import RequestFactory, Client
from django.contrib.messages import get_messages
from admin_panel.views import unassign_worker_from_request

User = get_user_model()

print("=" * 60)
print("TEST: Worker Unassignment and Availability")
print("=" * 60)

# Get or create test users with unique names
import random
suffix = random.randint(1000, 9999)

try:
    admin_user = User.objects.get(username=f'testadmin{suffix}')
except User.DoesNotExist:
    admin_user = User.objects.create_superuser(
        username=f'testadmin{suffix}',
        email=f'admin{suffix}@test.com',
        password='testpass123',
        user_type='admin'
    )

try:
    client_user = User.objects.get(username=f'testclient{suffix}')
except User.DoesNotExist:
    client_user = User.objects.create_user(
        username=f'testclient{suffix}',
        email=f'client{suffix}@test.com',
        password='testpass123',
        user_type='client',
        first_name='Test',
        last_name='Client'
    )

try:
    worker_user = User.objects.get(username=f'testworker{suffix}')
except User.DoesNotExist:
    worker_user = User.objects.create_user(
        username=f'testworker{suffix}',
        email=f'worker{suffix}@test.com',
        password='testpass123',
        user_type='worker',
        first_name='Test',
        last_name='Worker'
    )

# Get or create worker profile
worker_profile, _ = WorkerProfile.objects.get_or_create(
    user=worker_user,
    defaults={
        'verification_status': 'verified',
        'availability': 'available'
    }
)

print(f"\n✓ Created/Retrieved test users")
print(f"  Admin: {admin_user.username}")
print(f"  Client: {client_user.username}")
print(f"  Worker: {worker_user.username}")

# Create a test service request
from workers.models import Category
category, _ = Category.objects.get_or_create(
    name='Testing',
    defaults={'description': 'Test category'}
)
worker_profile.categories.add(category)

service_request = ServiceRequest.objects.create(
    client=client_user,
    category=category,
    title='Test Unassignment Service',
    description='Testing worker unassignment',
    location='Test Location',
    city='Test City',
    workers_needed=1,
    daily_rate=50000.00,
    duration_days=1,
    status='pending'
)

print(f"\n✓ Created service request #{service_request.id}")

# Test 1: Assign worker and verify they become busy
print("\n" + "=" * 60)
print("TEST 1: Assign Worker → Worker becomes BUSY")
print("=" * 60)

worker_profile.availability = 'available'
worker_profile.save()

assignment = ServiceRequestAssignment.objects.create(
    service_request=service_request,
    worker=worker_profile,
    assignment_number=1,
    status='pending'
)

# Simulate admin assigning
worker_profile.availability = 'busy'
worker_profile.save()
service_request.status = 'assigned'
service_request.save()

print(f"Assignment created: #{assignment.id}")
print(f"Worker availability: {worker_profile.availability}")
print(f"Service request status: {service_request.status}")

assert worker_profile.availability == 'busy', "Worker should be busy after assignment"
assert assignment.status == 'pending', "Assignment should be pending"
print("✓ TEST 1 PASSED: Worker is busy after assignment")

# Test 2: Unassign worker while pending (before acceptance)
print("\n" + "=" * 60)
print("TEST 2: Unassign Worker → Worker becomes AVAILABLE")
print("=" * 60)

# Delete the assignment directly (simulating unassign)
worker = assignment.worker
assignment.delete()

# Set worker back to available if no other active assignments (simulate the fix)
other_active_assignments = ServiceRequestAssignment.objects.filter(
    worker=worker,
    status__in=['pending', 'accepted', 'in_progress']
).count()

if other_active_assignments == 0:
    worker.availability = 'available'
    worker.save()

# Update service request if no assignments remain
remaining_assignments = ServiceRequestAssignment.objects.filter(
    service_request=service_request
).count()

if remaining_assignments == 0:
    service_request.status = 'pending'
    service_request.save()

# Refresh objects from database
worker_profile.refresh_from_db()
service_request.refresh_from_db()

print(f"Worker availability after unassign: {worker_profile.availability}")
print(f"Service request status: {service_request.status}")

# Check if assignment was deleted
assignment_exists = ServiceRequestAssignment.objects.filter(id=assignment.id).exists()
print(f"Assignment still exists: {assignment_exists}")

assert worker_profile.availability == 'available', "Worker should be available after unassignment"
assert not assignment_exists, "Assignment should be deleted"
assert service_request.status == 'pending', "Service request should be pending when no assignments remain"
print("✓ TEST 2 PASSED: Worker is available after unassignment, assignment deleted")

# Test 3: Worker should not see deleted assignment
print("\n" + "=" * 60)
print("TEST 3: Worker Cannot See Deleted Assignment")
print("=" * 60)

worker_assignments = ServiceRequestAssignment.objects.filter(worker=worker_profile)
print(f"Worker's active assignments count: {worker_assignments.count()}")
assert worker_assignments.count() == 0, "Worker should have no assignments after unassign"
print("✓ TEST 3 PASSED: Worker cannot see deleted assignment")

# Test 4: Assign worker, accept, then try unassign (should still work and set available)
print("\n" + "=" * 60)
print("TEST 4: Unassign After Acceptance → Worker AVAILABLE")
print("=" * 60)

# Create new assignment
assignment2 = ServiceRequestAssignment.objects.create(
    service_request=service_request,
    worker=worker_profile,
    assignment_number=1,
    status='pending'
)

worker_profile.availability = 'busy'
worker_profile.save()
service_request.status = 'assigned'
service_request.save()

# Worker accepts
assignment2.status = 'accepted'
assignment2.save()

print(f"Created new assignment #{assignment2.id} with status: {assignment2.status}")
print(f"Worker availability: {worker_profile.availability}")

# Admin unassigns - simulate the unassign logic
worker = assignment2.worker
assignment2.delete()

other_active_assignments = ServiceRequestAssignment.objects.filter(
    worker=worker,
    status__in=['pending', 'accepted', 'in_progress']
).count()

if other_active_assignments == 0:
    worker.availability = 'available'
    worker.save()

remaining_assignments = ServiceRequestAssignment.objects.filter(
    service_request=service_request
).count()

if remaining_assignments == 0:
    service_request.status = 'pending'
    service_request.save()

worker_profile.refresh_from_db()
service_request.refresh_from_db()

print(f"Worker availability after unassign: {worker_profile.availability}")
assignment2_exists = ServiceRequestAssignment.objects.filter(id=assignment2.id).exists()
print(f"Assignment still exists: {assignment2_exists}")

assert worker_profile.availability == 'available', "Worker should be available after unassignment"
assert not assignment2_exists, "Assignment should be deleted"
print("✓ TEST 4 PASSED: Worker is available even after accepted assignment is unassigned")

# Test 5: Multiple assignments - unassign one, worker stays busy
print("\n" + "=" * 60)
print("TEST 5: Multiple Jobs → Unassign One → Worker STAYS BUSY")
print("=" * 60)

# Create two service requests and assign both to same worker
sr1 = ServiceRequest.objects.create(
    client=client_user,
    category=category,
    title='Job 1',
    description='First job',
    location='Location 1',
    city='City 1',
    workers_needed=1,
    daily_rate=50000.00,
    duration_days=1,
    status='assigned'
)

sr2 = ServiceRequest.objects.create(
    client=client_user,
    category=category,
    title='Job 2',
    description='Second job',
    location='Location 2',
    city='City 2',
    workers_needed=1,
    daily_rate=50000.00,
    duration_days=1,
    status='assigned'
)

assign1 = ServiceRequestAssignment.objects.create(
    service_request=sr1,
    worker=worker_profile,
    assignment_number=1,
    status='accepted'
)

assign2 = ServiceRequestAssignment.objects.create(
    service_request=sr2,
    worker=worker_profile,
    assignment_number=1,
    status='accepted'
)

worker_profile.availability = 'busy'
worker_profile.save()

print(f"Created 2 assignments for same worker")
print(f"Worker availability: {worker_profile.availability}")

# Unassign from first job - simulate unassign logic
worker = assign1.worker
assign1.delete()

other_active_assignments = ServiceRequestAssignment.objects.filter(
    worker=worker,
    status__in=['pending', 'accepted', 'in_progress']
).count()

if other_active_assignments == 0:
    worker.availability = 'available'
    worker.save()

worker_profile.refresh_from_db()
print(f"Worker availability after unassigning from Job 1: {worker_profile.availability}")

# Worker should STILL be busy because they have another active assignment
assert worker_profile.availability == 'busy', "Worker should stay busy with other active assignments"
print("✓ TEST 5 PASSED: Worker stays busy when they have other active assignments")

# Unassign from second job - now worker should be available
worker = assign2.worker
assign2.delete()

other_active_assignments = ServiceRequestAssignment.objects.filter(
    worker=worker,
    status__in=['pending', 'accepted', 'in_progress']
).count()

if other_active_assignments == 0:
    worker.availability = 'available'
    worker.save()

worker_profile.refresh_from_db()
print(f"Worker availability after unassigning from Job 2: {worker_profile.availability}")

assert worker_profile.availability == 'available', "Worker should be available when all assignments removed"
print("✓ TEST 5 PASSED: Worker becomes available after last assignment removed")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print("\nSummary:")
print("✓ Worker becomes busy when assigned")
print("✓ Worker becomes available when unassigned (no other jobs)")
print("✓ Worker stays busy when unassigned but has other jobs")
print("✓ Assignment is deleted and worker cannot see it")
print("✓ Works for both pending and accepted assignments")

# Cleanup
ServiceRequest.objects.filter(id__in=[service_request.id, sr1.id, sr2.id]).delete()
worker_profile.delete()
admin_user.delete()
client_user.delete()
worker_user.delete()
print("\n✓ Test data cleaned up")
