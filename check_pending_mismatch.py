"""
Check pending assignments mismatch between old and new system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from workers.models import WorkerProfile

# Get the test worker - try different usernames
from django.contrib.auth import get_user_model
User = get_user_model()

# List all workers
all_workers = WorkerProfile.objects.all()
print(f"Total workers in database: {all_workers.count()}")
for w in all_workers:
    print(f"  - {w.user.get_full_name()} (@{w.user.username})")

# Get first worker
worker = all_workers.first()

if not worker:
    print("❌ No workers found in database")
    exit()

print(f"Worker: {worker.user.get_full_name()} (@{worker.user.username})")
print("=" * 70)

# OLD SYSTEM (used by dashboard)
print("\n=== OLD SYSTEM (Dashboard Query) ===")
old_pending = ServiceRequest.objects.filter(
    assigned_worker=worker,
    status='assigned',
    worker_accepted__isnull=True
)
print(f"Count: {old_pending.count()}")
for sr in old_pending:
    print(f"  - ID: {sr.id}, Title: {sr.title}, Status: {sr.status}")

# NEW SYSTEM (used by pending page)
print("\n=== NEW SYSTEM (Pending Page Query) ===")
new_pending = ServiceRequestAssignment.objects.filter(
    worker=worker,
    status='pending'
)
print(f"Count: {new_pending.count()}")
for sa in new_pending:
    print(f"  - ID: {sa.id}, Service: {sa.service_request.title}, Status: {sa.status}")

# Check all assignments for this worker
print("\n=== ALL ASSIGNMENTS (All Statuses) ===")
all_assignments = ServiceRequestAssignment.objects.filter(worker=worker)
print(f"Total Count: {all_assignments.count()}")
for sa in all_assignments:
    print(f"  - ID: {sa.id}, Service: {sa.service_request.title}, Status: {sa.status}, Accepted: {sa.worker_accepted}")

# Check service requests assigned to this worker
print("\n=== ALL SERVICE REQUESTS ===")
all_requests = ServiceRequest.objects.filter(assigned_worker=worker)
print(f"Total Count: {all_requests.count()}")
for sr in all_requests:
    print(f"  - ID: {sr.id}, Title: {sr.title}, Status: {sr.status}, Worker Accepted: {sr.worker_accepted}")

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("If dashboard shows 1 but pending page shows 0:")
print("  -> Dashboard is using OLD system, pending page uses NEW system")
print("  -> Need to update dashboard to use ServiceRequestAssignment")
