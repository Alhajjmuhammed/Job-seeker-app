import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from workers.models import WorkerProfile
from jobs.service_request_models import ServiceRequest, TimeTracking
from jobs.service_request_serializers import ServiceRequestSerializer
import traceback
import json

User = get_user_model()

print("\n" + "="*80)
print("Testing Worker Current Assignment with Test Worker")
print("="*80)

try:
    # Get Test Worker
    worker_user = User.objects.get(email='worker@test.com')
    print(f"\n✓ Found worker: {worker_user.get_full_name()} ({worker_user.email})")
    
    worker_profile = WorkerProfile.objects.get(user=worker_user)
    print(f"✓ Worker profile: {worker_profile}")
    
    # Get current assignment
    current = ServiceRequest.objects.filter(
        assigned_worker=worker_profile,
        status='in_progress'
    ).select_related('client', 'category').first()
    
    if current:
        print(f"\n✓ Found current assignment:")
        print(f"  ID: {current.id}")
        print(f"  Title: {current.title}")
        print(f"  Status: {current.status}")
        print(f"  Client: {current.client}")
        print(f"  Category: {current.category}")
        
        # Try serialization
        print("\n" + "-"*80)
        print("Testing Serialization:")
        print("-"*80)
        
        try:
            serializer = ServiceRequestSerializer(current)
            data = serializer.data
            print(f"✓ Serialization successful!")
            print(f"  Keys in data: {list(data.keys())}")
            
            # Check for clock-in status
            active_clock = TimeTracking.objects.filter(
                service_request=current,
                worker=worker_profile,
                clock_out__isnull=True
            ).first()
            
            print(f"\n✓ Clock-in check:")
            print(f"  Active clock: {active_clock}")
            print(f"  Is clocked in: {active_clock is not None}")
            print(f"  Clock in time: {active_clock.clock_in if active_clock else None}")
            
            # Build response
            response_data = {
                'service_request': data,
                'is_clocked_in': active_clock is not None,
                'clock_in_time': str(active_clock.clock_in) if active_clock else None
            }
            
            print(f"\n✓ Response structure:")
            print(f"  Has service_request: {('service_request' in response_data)}")
            print(f"  Has is_clocked_in: {('is_clocked_in' in response_data)}")
            print(f"  Has clock_in_time: {('clock_in_time' in response_data)}")
            
            # Try to convert to JSON
            try:
                json_str = json.dumps(response_data, default=str)
                print(f"\n✓ JSON serialization successful")
                print(f"  JSON length: {len(json_str)} characters")
            except Exception as json_error:
                print(f"\n✗ JSON serialization ERROR:")
                print(f"  {type(json_error).__name__}: {json_error}")
                
        except Exception as ser_error:
            print(f"\n✗ SERIALIZATION ERROR:")
            print(f"  {type(ser_error).__name__}: {ser_error}")
            traceback.print_exc()
            
    else:
        print(f"\n✗ No current assignment found")
        
except User.DoesNotExist:
    print(f"\n✗ Worker not found: worker@test.com")
except Exception as e:
    print(f"\n✗ ERROR:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n" + "="*80)
