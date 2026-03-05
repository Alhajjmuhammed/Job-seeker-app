import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from workers.models import WorkerProfile
from jobs.service_request_models import ServiceRequest
import traceback

User = get_user_model()

print("\n" + "="*80)
print("Testing Worker Current Assignment Endpoint")
print("="*80)

# Find a worker user
workers = User.objects.filter(user_type='worker')
print(f"\nFound {workers.count()} worker users")

if workers.exists():
    worker_user = workers.first()
    print(f"\nTesting with worker: {worker_user.email} (ID: {worker_user.id})")
    
    try:
        worker_profile = WorkerProfile.objects.get(user=worker_user)
        print(f"✓ Worker profile found: {worker_profile}")
        
        # Check for in_progress assignments
        current = ServiceRequest.objects.filter(
            assigned_worker=worker_profile,
            status='in_progress'
        ).select_related('client', 'category').first()
        
        if current:
            print(f"\n✓ Found current assignment: {current}")
            print(f"  - ID: {current.id}")
            print(f"  - Title: {current.title}")
            print(f"  - Status: {current.status}")
            print(f"  - Client: {current.client}")
            print(f"  - Category: {current.category}")
            
            # Try to serialize
            from jobs.service_request_serializers import ServiceRequestSerializer
            try:
                serializer = ServiceRequestSerializer(current)
                print(f"\n✓ Serialization successful")
                print(f"  Data keys: {serializer.data.keys()}")
            except Exception as e:
                print(f"\n✗ SERIALIZATION ERROR:")
                print(f"  {type(e).__name__}: {e}")
                traceback.print_exc()
        else:
            print(f"\n✓ No active assignment (status='in_progress')")
            
            # Check all assignments for this worker
            all_assignments = ServiceRequest.objects.filter(assigned_worker=worker_profile)
            print(f"\nAll assignments for this worker: {all_assignments.count()}")
            for sr in all_assignments:
                print(f"  - [{sr.id}] {sr.title} - Status: {sr.status}")
            
    except WorkerProfile.DoesNotExist:
        print(f"✗ Worker profile not found for user {worker_user.email}")
    except Exception as e:
        print(f"\n✗ ERROR:")
        print(f"  {type(e).__name__}: {e}")
        traceback.print_exc()
else:
    print("\n✗ No worker users found in database")

print("\n" + "="*80)
