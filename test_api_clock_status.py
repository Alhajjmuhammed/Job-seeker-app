"""
Test the worker assignment detail API endpoint directly
to see what is_clocked_in value it returns
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from workers.assignment_views import worker_assignment_detail
from workers.models import WorkerProfile

User = get_user_model()

print("=" * 80)
print("TESTING API ENDPOINT: /api/v1/worker/my-assignments/84/")
print("=" * 80)

# Get the test worker
try:
    worker_user = User.objects.get(username='worker')  # ID: 2
    worker_profile = WorkerProfile.objects.get(user=worker_user)
    
    # Create a fake request
    factory = RequestFactory()
    request = factory.get('/api/v1/worker/my-assignments/84/')
    request.user = worker_user
    
    # Call the view
    response = worker_assignment_detail(request, 84)
    
    print(f"\n✅ API Response Status: {response.status_code}")
    
    if response.status_code == 200:
        # Render the response first if it's a TemplateResponse
        if hasattr(response, 'render'):
            response.render()
        
        data = json.loads(response.content)
        
        print(f"\n📊 Response Data:")
        print(f"   is_clocked_in: {data.get('is_clocked_in')}")
        print(f"   time_logs count: {len(data.get('time_logs', []))}")
        print(f"   assignment.status: {data.get('assignment', {}).get('status')}")
        print(f"   total_hours_worked: {data.get('total_hours_worked')}")
        
        print(f"\n🕐 Time Logs Detail:")
        for i, log in enumerate(data.get('time_logs', []), 1):
            clock_out = log.get('clock_out')
            status = '🟢 ACTIVE (no clock_out)' if not clock_out else f'✅ Complete (clock_out: {clock_out})'
            print(f"   {i}. {status}")
        
        # Count active logs manually
        active_count = sum(1 for log in data.get('time_logs', []) if not log.get('clock_out'))
        print(f"\n🔍 Manual Check:")
        print(f"   Active logs (clock_out=None): {active_count}")
        print(f"   API says is_clocked_in: {data.get('is_clocked_in')}")
        
        if active_count == 0 and data.get('is_clocked_in') == True:
            print(f"\n⚠️ BUG FOUND: API returns is_clocked_in=True but no active time logs!")
        elif active_count > 0 and data.get('is_clocked_in') == False:
            print(f"\n⚠️ BUG FOUND: API returns is_clocked_in=False but has {active_count} active log(s)!")
        else:
            print(f"\n✅ is_clocked_in is CORRECT")
    else:
        print(f"\n❌ Error: {response.content}")
        
except User.DoesNotExist:
    print("❌ Test worker not found. Please create with username='testworker'")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
