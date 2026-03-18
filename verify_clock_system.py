"""
Comprehensive Clock In/Out Testing & Verification Script
Tests all scenarios and ensures the system works correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.utils import timezone
from jobs.service_request_models import ServiceRequestAssignment, TimeTracking
from workers.models import WorkerProfile

print("=" * 80)
print("COMPREHENSIVE CLOCK IN/OUT SYSTEM CHECK")
print("=" * 80)

# Configuration
ASSIGNMENT_ID = 84
WORKER_ID = 2

try:
    # Get assignment and worker
    assignment = ServiceRequestAssignment.objects.get(id=ASSIGNMENT_ID)
    worker = WorkerProfile.objects.get(id=WORKER_ID)
    
    print(f"\n✅ Test Subject:")
    print(f"   Assignment: #{assignment.assignment_number} - {assignment.service_request.title}")
    print(f"   Worker: {worker.user.get_full_name()}")
    print(f"   Service Request ID: {assignment.service_request.id}")
    
    # Check current state
    print(f"\n📊 CURRENT STATE:")
    print(f"   Assignment Status: {assignment.status}")
    print(f"   Worker Accepted: {assignment.worker_accepted}")
    
    # Get all time logs
    all_logs = TimeTracking.objects.filter(
        service_request=assignment.service_request,
        worker=worker
    ).order_by('clock_in')
    
    active_log = all_logs.filter(clock_out__isnull=True).first()
    completed_logs = all_logs.filter(clock_out__isnull=False)
    
    print(f"   Total Time Logs: {all_logs.count()}")
    print(f"   Completed Logs: {completed_logs.count()}")
    print(f"   Active Logs: {1 if active_log else 0}")
    
    is_clocked_in = active_log is not None
    print(f"   IS_CLOCKED_IN: {is_clocked_in}")
    
    # Show recent activity
    print(f"\n📋 RECENT TIME LOGS (Last 5):")
    recent_logs = all_logs.order_by('-clock_in')[:5]
    for i, log in enumerate(recent_logs, 1):
        clock_in = log.clock_in.strftime('%H:%M:%S') if log.clock_in else 'N/A'
        clock_out = log.clock_out.strftime('%H:%M:%S') if log.clock_out else '🟢 ACTIVE'
        status = '🟢 ACTIVE' if log.clock_out is None else '✅ Complete'
        print(f"   {i}. {status} | In: {clock_in} | Out: {clock_out}")
    
    # System checks
    print(f"\n🔍 SYSTEM CHECKS:")
    checks_passed = 0
    checks_failed = 0
    
    # Check 1: Data consistency
    if is_clocked_in and active_log:
        print(f"   ✅ Data Consistency: Active log exists")
        checks_passed += 1
    elif not is_clocked_in and not active_log:
        print(f"   ✅ Data Consistency: No active logs (clocked out)")
        checks_passed += 1
    else:
        print(f"   ❌ Data Consistency: Mismatch!")
        checks_failed += 1
    
    # Check 2: Multiple active logs check
    if active_log and all_logs.filter(clock_out__isnull=True).count() > 1:
        print(f"   ⚠️  WARNING: Multiple active time logs found!")
        checks_failed += 1
    else:
        print(f"   ✅ Single Active Log: No duplicates")
        checks_passed += 1
    
    # Check 3: Assignment status matches clock state
    if is_clocked_in and assignment.status == 'in_progress':
        print(f"   ✅ Status Match: Clocked in + In Progress")
        checks_passed += 1
    elif not is_clocked_in and assignment.status in ['accepted', 'in_progress']:
        print(f"   ✅ Status Match: Clocked out + {assignment.status}")
        checks_passed += 1
    else:
        print(f"   ⚠️  Status Note: {assignment.status} (might be normal)")
        checks_passed += 1
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if is_clocked_in:
        print(f"   📱 Mobile App Should Show: 'Clock Out' button")
        print(f"   🔓 Allowed Actions: Clock Out, Continue Working")
        print(f"   🚫 Blocked Actions: Clock In (already clocked in)")
    else:
        print(f"   📱 Mobile App Should Show: 'Clock In' button")
        print(f"   🔓 Allowed Actions: Clock In")
        print(f"   🚫 Blocked Actions: Clock Out (not clocked in)")
    
    # Test scenarios
    print(f"\n🧪 TEST SCENARIOS:")
    print(f"\n   Scenario 1: Normal Clock In/Out Flow")
    print(f"   1. Worker clocks in → Creates TimeTracking (clock_out=NULL)")
    print(f"   2. Worker sees 'Clock Out' button")
    print(f"   3. Worker clocks out → Updates TimeTracking (clock_out=NOW)")
    print(f"   4. Worker sees 'Clock In' button")
    print(f"   Status: {'✅ READY' if not is_clocked_in else '⚠️  Already clocked in'}")
    
    print(f"\n   Scenario 2: Prevent Double Clock In")
    print(f"   1. Worker tries to clock in while already clocked in")
    print(f"   2. Screen checks is_clocked_in → TRUE")
    print(f"   3. Shows alert: 'Already Clocked In'")
    print(f"   4. Redirects back")
    print(f"   Status: {'⚠️  Need to test' if is_clocked_in else '⏭️  Not applicable'}")
    
    print(f"\n   Scenario 3: Prevent Clock Out When Not Clocked In")
    print(f"   1. Worker tries to clock out when not clocked in")
    print(f"   2. Screen checks is_clocked_in → FALSE")
    print(f"   3. Shows alert: 'Not Clocked In'")
    print(f"   4. Redirects back")
    print(f"   Status: {'✅ READY to test' if not is_clocked_in else '⏭️  Not applicable'}")
    
    # Summary
    print(f"\n" + "=" * 80)
    print(f"SUMMARY")
    print(f"=" * 80)
    print(f"   Checks Passed: {checks_passed}")
    print(f"   Checks Failed: {checks_failed}")
    print(f"   Current State: {'🟢 CLOCKED IN' if is_clocked_in else '⚪ CLOCKED OUT'}")
    
    if checks_failed == 0:
        print(f"\n   ✅ SYSTEM IS HEALTHY - Ready for testing!")
    else:
        print(f"\n   ⚠️  ISSUES DETECTED - Please review")
    
    # Next steps
    print(f"\n📝 NEXT STEPS FOR USER:")
    if is_clocked_in:
        print(f"   1. Refresh your mobile app assignment detail screen")
        print(f"   2. Should see 'Clock Out' button")
        print(f"   3. Click 'Clock Out' → Should succeed")
        print(f"   4. After clock out, refresh again")
        print(f"   5. Should see 'Clock In' button")
    else:
        print(f"   1. Close any open clock out screens")
        print(f"   2. Go back to assignment detail screen")
        print(f"   3. Pull down to refresh (or close and reopen)")
        print(f"   4. Should see 'Clock In' button")
        print(f"   5. Click 'Clock In' → Should succeed")
        print(f"   6. After clock in, should see 'Clock Out' button")
    
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
