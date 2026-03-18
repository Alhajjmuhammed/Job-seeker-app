"""
Debug script to check clock in/out status for assignment #84
This helps diagnose why backend says "not clocked in" when frontend shows "clocked in"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequestAssignment, TimeTracking
from workers.models import WorkerProfile

# Check assignment #84
assignment_id = 84

print("=" * 80)
print(f"DEBUGGING ASSIGNMENT #{assignment_id}")
print("=" * 80)

try:
    assignment = ServiceRequestAssignment.objects.get(id=assignment_id)
    print(f"\n✅ Assignment Found:")
    print(f"   ID: {assignment.id}")
    print(f"   Number: #{assignment.assignment_number}")
    print(f"   Status: {assignment.status}")
    print(f"   Worker: {assignment.worker.user.get_full_name()} (ID: {assignment.worker.id})")
    print(f"   Service Request: {assignment.service_request.title} (ID: {assignment.service_request.id})")
    print(f"   Worker Accepted: {assignment.worker_accepted}")
    
    # Get all time logs for this worker + service request
    time_logs = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=assignment.worker
    ).order_by('clock_in')
    
    print(f"\n📊 Time Logs (Total: {time_logs.count()}):")
    print("-" * 80)
    
    for i, log in enumerate(time_logs, 1):
        clock_in_str = log.clock_in.strftime('%Y-%m-%d %H:%M:%S') if log.clock_in else 'None'
        clock_out_str = log.clock_out.strftime('%Y-%m-%d %H:%M:%S') if log.clock_out else 'NOT CLOCKED OUT'
        status_icon = '🟢 ACTIVE' if log.clock_out is None else '✅ Complete'
        
        print(f"{i}. {status_icon}")
        print(f"   Clock In:  {clock_in_str}")
        print(f"   Clock Out: {clock_out_str}")
        print(f"   Duration:  {log.duration_hours or 'N/A'} hours")
        print(f"   Location:  {log.clock_in_location or 'N/A'}")
        if log.notes:
            print(f"   Notes:     {log.notes[:50]}")
        print()
    
    # Check for ACTIVE clock in (clock_out is NULL)
    active_logs = time_logs.filter(clock_out__isnull=True)
    
    print("=" * 80)
    print(f"🔍 ACTIVE TIME LOG CHECK:")
    print(f"   Query: service_request={assignment.service_request.id}, worker={assignment.worker.id}, clock_out=NULL")
    print(f"   Result: {active_logs.count()} active log(s) found")
    
    if active_logs.exists():
        active_log = active_logs.first()
        print(f"\n   ✅ WORKER IS CLOCKED IN")
        print(f"   Clock In Time: {active_log.clock_in}")
        print(f"   Duration So Far: {(django.utils.timezone.now() - active_log.clock_in).total_seconds() / 3600:.2f} hours")
    else:
        print(f"\n   ❌ WORKER IS NOT CLOCKED IN")
        print(f"   All {time_logs.count()} time logs have been clocked out")
        print(f"\n   💡 DIAGNOSIS:")
        print(f"   The frontend shows 'isClockedIn: true' but backend says 'not clocked in'")
        print(f"   This means the worker already clocked out, but the frontend cache is stale.")
        print(f"   The worker needs to:")
        print(f"   1. Go back to assignment detail screen")
        print(f"   2. Pull to refresh or reopen the screen")
        print(f"   3. Should see 'Clock In' button instead of 'Clock Out'")
    
    print("=" * 80)
    
except ServiceRequestAssignment.DoesNotExist:
    print(f"\n❌ Assignment #{assignment_id} not found")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
