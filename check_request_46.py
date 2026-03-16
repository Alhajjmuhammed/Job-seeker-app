"""Check service request 46 details"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.models import ServiceRequest, ServiceRequestAssignment

sr = ServiceRequest.objects.get(id=46)
print(f"Service Request #46: {sr.title}")
print(f"workers_needed: {sr.workers_needed}")
print(f"assigned_worker: {sr.assigned_worker}")
print(f"worker_accepted: {sr.worker_accepted}")
print(f"Status: {sr.status}")

assignments = ServiceRequestAssignment.objects.filter(service_request=sr)
print(f"\nTotal Assignments: {assignments.count()}")

for assignment in assignments:
    print(f"\nAssignment #{assignment.assignment_number}")
    print(f"  Worker: {assignment.worker.user.get_full_name()}")
    print(f"  Status: {assignment.status}")
    print(f"  Has profile image: {bool(assignment.worker.profile_image)}")

# Check what template condition would match
print("\n--- Template Condition Check ---")
print(f"workers_needed > 1: {sr.workers_needed and sr.workers_needed > 1}")
print(f"Has assignments: {assignments.exists()}")
print(f"First condition (multiple): {sr.workers_needed and sr.workers_needed > 1 and assignments.exists()}")
print(f"Second condition (legacy single): {bool(sr.assigned_worker and sr.worker_accepted)}")

# Show what should work
accepted_assignments = assignments.filter(status__in=['accepted', 'in_progress', 'completed'])
print(f"\nAccepted assignments count: {accepted_assignments.count()}")
