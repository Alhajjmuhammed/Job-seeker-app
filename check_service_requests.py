import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*80)
print("Checking All Service Requests")
print("="*80)

all_requests = ServiceRequest.objects.all().select_related('client', 'assigned_worker')
print(f"\nTotal Service Requests: {all_requests.count()}")

for sr in all_requests:
    worker_info = f"Worker: {sr.assigned_worker.user.get_full_name() if sr.assigned_worker else 'UNASSIGNED'}"
    print(f"\n[{sr.id}] {sr.title}")
    print(f"  Status: {sr.status}")
    print(f"  Client: {sr.client.get_full_name()}")
    print(f"  {worker_info}")
    
print("\n" + "="*80)
print("Workers with their assignments:")
print("="*80)

workers = User.objects.filter(user_type='worker')
for worker in workers:
    assignments = ServiceRequest.objects.filter(assigned_worker__user=worker)
    print(f"\n{worker.get_full_name()} ({worker.email}):")
    if assignments.exists():
        for sr in assignments:
            print(f"  - [{sr.id}] {sr.title} - {sr.status}")
    else:
        print(f"  No assignments")

print("\n" + "="*80)
