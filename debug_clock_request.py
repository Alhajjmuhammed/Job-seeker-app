#!/usr/bin/env python
"""
Debug script to trace what's happening with clock out requests
Shows request logs and database state
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequestAssignment, TimeTracking
from workers.models import WorkerProfile
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def debug_clock_out_issue():
    print("\n" + "="*80)
    print("🔍 CLOCK OUT REQUEST DEBUG")
    print("="*80)
    
    # Get worker and assignment
    try:
        worker_user = User.objects.filter(email='worker@test.com').first()
        if not worker_user:
            print("❌ Worker not found")
            return
        
        worker_profile = WorkerProfile.objects.get(user=worker_user)
        assignment = ServiceRequestAssignment.objects.get(id=84)
        
        print(f"\n📊 CURRENT STATE:")
        print(f"   Worker: {worker_user.email}")
        print(f"   Assignment ID: {assignment.id}")
        print(f"   Service Request: {assignment.service_request.title}")
        print(f"   Assignment Status: {assignment.status}")
        
        # Check active time logs
        active_logs = TimeTracking.objects.filter(
            service_request=assignment.service_request,
            worker=worker_profile,
            clock_out__isnull=True
        )
        
        print(f"\n🕐 ACTIVE TIME LOGS (clock_out IS NULL):")
        if active_logs.exists():
            for log in active_logs:
                print(f"   ✅ Log #{log.id}")
                print(f"      Clock In:  {log.clock_in}")
                print(f"      Clock Out: {log.clock_out} (STILL ACTIVE)")
                print(f"      Duration:  Currently working...")
        else:
            print(f"   ❌ NO ACTIVE LOGS - Worker is NOT clocked in")
        
        # Get ALL time logs
        all_logs = TimeTracking.objects.filter(
            service_request=assignment.service_request,
            worker=worker_profile
        ).order_by('-clock_in')
        
        print(f"\n📜 ALL TIME LOGS (Total: {all_logs.count()}):")
        for i, log in enumerate(all_logs[:5], 1):
            status_icon = "⏳" if log.clock_out is None else "✅"
            print(f"   {status_icon} Log #{log.id}")
            print(f"      Clock In:  {log.clock_in}")
            if log.clock_out:
                duration = (log.clock_out - log.clock_in).total_seconds()
                print(f"      Clock Out: {log.clock_out}")
                print(f"      Duration:  {duration:.1f} seconds ({duration/3600:.2f} hours)")
            else:
                print(f"      Clock Out: NULL (ACTIVE)")
                duration = (timezone.now() - log.clock_in).total_seconds()
                print(f"      Duration:  {duration:.1f} seconds (ongoing)")
        
        print(f"\n🎯 WHAT SHOULD HAPPEN:")
        if active_logs.exists():
            print(f"   ✅ Clock out API should SUCCEED")
            print(f"   ✅ Should find active log and clock it out")
            print(f"   ✅ Should return 200 with time log data")
        else:
            print(f"   ❌ Clock out API should FAIL with 400")
            print(f"   ❌ Should return: 'You are not clocked in. Please clock in first.'")
            print(f"   ℹ️ Worker needs to clock IN first")
        
        print(f"\n💡 BACKEND LOGIC:")
        print(f"   1. Find active log: TimeTracking.objects.filter(")
        print(f"         service_request={assignment.service_request.id},")
        print(f"         worker={worker_profile.id},")
        print(f"         clock_out__isnull=True")
        print(f"      ).first()")
        print(f"   2. If active_log exists → Clock out and return 200")
        print(f"   3. If active_log is None → Return 400 'not clocked in'")
        
        # Check for timing issues
        recent_logs = TimeTracking.objects.filter(
            service_request=assignment.service_request,
            worker=worker_profile,
            clock_in__gte=timezone.now() - timedelta(minutes=5)
        ).order_by('-clock_in')
        
        if recent_logs.count() > 1:
            print(f"\n⚠️ POTENTIAL ISSUE - Multiple logs in last 5 minutes:")
            for log in recent_logs:
                print(f"   Log #{log.id}: Clock In {log.clock_in}, Clock Out {log.clock_out}")
            print(f"   → This suggests duplicate requests were processed")
        
        # Check for race conditions
        incomplete_count = TimeTracking.objects.filter(
            service_request=assignment.service_request,
            worker=worker_profile,
            clock_out__isnull=True
        ).count()
        
        if incomplete_count > 1:
            print(f"\n🚨 CRITICAL ISSUE - Multiple active logs:")
            print(f"   Found {incomplete_count} logs with NULL clock_out")
            print(f"   → This indicates a race condition or duplicate clock in")
            print(f"   → System should only allow ONE active log at a time")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_clock_out_issue()
