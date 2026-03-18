"""
Step-by-step comparison: Web vs Mobile Clock Out
Trace EVERY step to find the difference
"""
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import TimeTracking
from workers.models import WorkerProfile

print("=" * 100)
print("STEP-BY-STEP TRACE: WEB vs MOBILE CLOCK OUT")
print("=" * 100)

worker = WorkerProfile.objects.get(id=2)
service_request_id = 46

# Get time logs
logs = TimeTracking.objects.filter(
    service_request_id=service_request_id,
    worker=worker
).order_by('-clock_in')[:3]

print("\n📋 LAST 3 TIME LOGS (Most Recent First):")
print("-" * 100)
for i, log in enumerate(logs, 1):
    clock_in = log.clock_in.strftime('%H:%M:%S.%f')[:-3]  # Show milliseconds
    if log.clock_out:
        clock_out = log.clock_out.strftime('%H:%M:%S.%f')[:-3]
        diff = (log.clock_out - log.clock_in).total_seconds()
        print(f"{i}. Clock In:  {clock_in}")
        print(f"   Clock Out: {clock_out}")
        print(f"   Duration:  {diff:.3f} seconds")
        print(f"   Location:  {log.clock_out_location or 'None'}")
        print(f"   Notes:     {log.notes or 'None'}")
    else:
        print(f"{i}. Clock In:  {clock_in}")
        print(f"   Clock Out: 🟢 STILL ACTIVE")
    print()

print("=" * 100)
print("WEB FLOW (works perfectly):")
print("=" * 100)
print("""
1. User on assignment detail page → Clicks "Clock Out" link
2. GET request to /worker/assignments/{id}/clock-out/
3. Backend:
   a. Find assignment (by worker + assignment ID)
   b. Find active TimeTracking (clock_out__isnull=True)
   c. If no active log → Show error page "No active clock-in found"
   d. If active log → Show clock out form (location, notes)
4. User fills form → Clicks "Submit"  
5. POST request to /worker/assignments/{id}/clock-out/
6. Backend:
   a. Find assignment
   b. Find active TimeTracking (again!)
   c. If no active log → Redirect with error
   d. If active log exists:
      - Set clock_out = now()
      - Set location and notes
      - Save
      - Log activity
      - Redirect to assignment detail
7. User sees success message

❓ KEY QUESTION: Does the form have any JavaScript that could submit twice?
✅ KEY PROTECTION: Server checks for active log TWICE (GET and POST)
""")

print("=" * 100)
print("MOBILE FLOW (having issues):")
print("=" * 100)
print("""
1. User on assignment detail screen → Clicks "Clock Out" button
2. Navigator pushes to /(worker)/assignments/clock/out/{id}
3. Clock out screen loads:
   a. Calls getWorkerAssignmentDetail() - Gets assignment + is_clocked_in
   b. If !is_clocked_in → Shows alert → Redirects back
   c. If is_clocked_in → Shows clock out form
   d. Requests location permission
4. User clicks "Clock Out Now"
5. Confirmation Alert shows: "Yes, Clock Out"  ← POTENTIAL ISSUE HERE!
6. User clicks "Yes, Clock Out" on alert
7. confirmClockOut() function called:
   a. Check isProcessingRef (should prevent double call)
   b. Double-check: Call getWorkerAssignmentDetail() again
   c. Verify is_clocked_in still true
   d. If false → Alert + redirect
   e. If true → Call clockOut API
8. API Backend (SAME as web):
   a. Find assignment
   b. Find active TimeTracking
   c. If no active log → Return 400 error "not clocked in"
   d. If active log:
      - Set clock_out = now()
      - Save
      - Return success
9. Mobile receives response → Navigate back

❓ POTENTIAL ISSUES:
1. Alert confirmation button could be tapped multiple times quickly
2. isProcessingRef guard might not work if function called from different contexts
3. React Native might batch state updates causing race condition
4. Network request might be duplicated by Axios interceptor or retry logic
""")

print("=" * 100)
print("🔍 ANALYSIS OF YOUR LAST ATTEMPT:")
print("=" * 100)

most_recent = logs[0] if logs.count() > 0 else None
if most_recent:
    if most_recent.clock_out:
        clock_in_time = most_recent.clock_in
        clock_out_time = most_recent.clock_out
        duration = (clock_out_time - clock_in_time).total_seconds()
        
        print(f"Clock In:  {clock_in_time.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"Clock Out: {clock_out_time.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"Duration:  {duration:.3f} seconds ({duration:.0f}s ~ {duration * 1000:.0f}ms)")
        print()
        
        if duration < 1.0:
            print("⚠️  WARNING: Duration less than 1 second!")
            print("   This suggests you clocked in and immediately tried to clock out.")
            print("   This is likely a testing scenario.")
        elif duration < 30:
            print("⚠️  Very short work session (less than 30 seconds)")
        
        print()
        print("📊 What happened:")
        print("   ✅ Clock in succeeded")
        print("   ✅ Clock out succeeded (log created with clock_out time)")
        print("   ❌ But you also saw an error")
        print()
        print("💡 DIAGNOSIS:")
        print("   This means TWO clock-out requests were sent:")
        print("   - Request 1: Arrived first → Successfully clocked out")
        print("   - Request 2: Arrived after → Got 'not clocked in' error")
        print()
        print("🔧 LIKELY CAUSES:")
        print("   1. Double-tap on Alert 'Yes, Clock Out' button")
        print("   2. isProcessingRef guard not working (app not reloaded with new code)")
        print("   3. Something else triggering duplicate API call")

print("=" * 100)
print("🎯 SOLUTION:")
print("=" * 100)
print("""
The isProcessingRef guard I added SHOULD prevent this, but you need to:

1. ✅ FORCE RELOAD THE APP (old code is cached)
   - Completely close Expo Go app
   - Clear app data if possible
   - Reopen and reload

2. ✅ ALTERNATIVE: Add request debouncing at API level
   - Change the clockOut function in api.ts
   - Add a timestamp guard to prevent duplicate calls within 1 second

3. ✅ VERIFY the guard is working:
   - After reload, check logs for: "⚠️ Already processing clock out"
   - If you see this message, the guard is working

4. ✅ TEST CAREFULLY:
   - Clock in
   - Try to double-tap "Yes, Clock Out" as fast as possible
   - Should see guard message in console
   - Should only get ONE successful clock out (no error)
""")

print("=" * 100)
