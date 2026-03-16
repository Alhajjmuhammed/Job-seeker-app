"""
Clean All Service Requests - Start Fresh
Removes all ServiceRequest records and related data
Date: March 15, 2026
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.db import transaction
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking, WorkerActivity
from workers.models import WorkerProfile


def clean_all_service_requests():
    """Clean all service requests and reset worker availability"""
    
    print("=" * 70)
    print("🧹 CLEANING ALL SERVICE REQUESTS - STARTING FRESH")
    print("=" * 70)
    print()
    
    with transaction.atomic():
        # Count before deletion
        service_requests_count = ServiceRequest.objects.count()
        assignments_count = ServiceRequestAssignment.objects.count()
        time_tracking_count = TimeTracking.objects.count()
        activities_count = WorkerActivity.objects.count()
        
        print(f"📊 Current Records:")
        print(f"   - Service Requests: {service_requests_count}")
        print(f"   - Assignments: {assignments_count}")
        print(f"   - Time Tracking Logs: {time_tracking_count}")
        print(f"   - Worker Activities: {activities_count}")
        print()
        
        # Delete all related records
        print("🗑️  Deleting records...")
        
        # Delete worker activities related to service requests
        WorkerActivity.objects.filter(service_request__isnull=False).delete()
        print("   ✅ Worker activities deleted")
        
        # Delete time tracking logs
        TimeTracking.objects.all().delete()
        print("   ✅ Time tracking logs deleted")
        
        # Delete service request assignments
        ServiceRequestAssignment.objects.all().delete()
        print("   ✅ Service request assignments deleted")
        
        # Delete service requests
        ServiceRequest.objects.all().delete()
        print("   ✅ Service requests deleted")
        
        print()
        
        # Reset all workers to 'available' status
        busy_workers = WorkerProfile.objects.filter(availability='busy')
        busy_count = busy_workers.count()
        
        if busy_count > 0:
            print(f"🔄 Resetting {busy_count} busy workers to 'available'...")
            busy_workers.update(availability='available')
            print("   ✅ Workers reset to available")
        else:
            print("   ℹ️  No busy workers to reset")
        
        print()
        print("=" * 70)
        print("✅ CLEANUP COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("📋 Summary:")
        print(f"   - Deleted {service_requests_count} service requests")
        print(f"   - Deleted {assignments_count} assignments")
        print(f"   - Deleted {time_tracking_count} time tracking logs")
        print(f"   - Deleted {activities_count} worker activities")
        print(f"   - Reset {busy_count} workers to available")
        print()
        print("🎯 System is now clean and ready for fresh service requests!")
        print()


if __name__ == '__main__':
    # Confirm before proceeding
    print()
    print("⚠️  WARNING: This will DELETE ALL service requests and related data!")
    print()
    confirm = input("Are you sure you want to continue? Type 'yes' to proceed: ")
    
    if confirm.lower() == 'yes':
        print()
        clean_all_service_requests()
    else:
        print()
        print("❌ Cleanup cancelled.")
        print()
