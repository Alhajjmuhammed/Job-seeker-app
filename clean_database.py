#!/usr/bin/env python
"""
Script to clean old data from the database.
Removes all service requests, jobs, and related data while keeping users and categories.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest, TimeTracking, WorkerActivity
from jobs.models import JobRequest, JobApplication, DirectHireRequest, Message, SavedJob

def clean_database():
    """Clean old data from database"""
    print("🧹 Starting database cleanup...\n")
    
    # Count before deletion
    service_requests_count = ServiceRequest.objects.count()
    job_requests_count = JobRequest.objects.count()
    job_applications_count = JobApplication.objects.count()
    direct_hire_count = DirectHireRequest.objects.count()
    messages_count = Message.objects.count()
    time_tracking_count = TimeTracking.objects.count()
    worker_activity_count = WorkerActivity.objects.count()
    saved_jobs_count = SavedJob.objects.count()
    
    print(f"📊 Current data:")
    print(f"   - Service Requests: {service_requests_count}")
    print(f"   - Job Requests (old): {job_requests_count}")
    print(f"   - Job Applications: {job_applications_count}")
    print(f"   - Direct Hire Requests: {direct_hire_count}")
    print(f"   - Messages: {messages_count}")
    print(f"   - Time Tracking: {time_tracking_count}")
    print(f"   - Worker Activities: {worker_activity_count}")
    print(f"   - Saved Jobs: {saved_jobs_count}")
    print()
    
    # Delete all job and service request data
    print("🗑️  Deleting time tracking records...")
    TimeTracking.objects.all().delete()
    print("   ✅ Time tracking deleted")
    
    print("🗑️  Deleting worker activities...")
    WorkerActivity.objects.all().delete()
    print("   ✅ Worker activities deleted")
    
    print("🗑️  Deleting service requests...")
    ServiceRequest.objects.all().delete()
    print("   ✅ Service requests deleted")
    
    print("🗑️  Deleting messages...")
    Message.objects.all().delete()
    print("   ✅ Messages deleted")
    
    print("🗑️  Deleting saved jobs...")
    SavedJob.objects.all().delete()
    print("   ✅ Saved jobs deleted")
    
    print("🗑️  Deleting job applications...")
    JobApplication.objects.all().delete()
    print("   ✅ Job applications deleted")
    
    print("🗑️  Deleting direct hire requests...")
    DirectHireRequest.objects.all().delete()
    print("   ✅ Direct hire requests deleted")
    
    print("🗑️  Deleting old job requests...")
    JobRequest.objects.all().delete()
    print("   ✅ Old job requests deleted")
    
    # Verify deletion
    print()
    print("📊 After cleanup:")
    print(f"   - Service Requests: {ServiceRequest.objects.count()}")
    print(f"   - Job Requests: {JobRequest.objects.count()}")
    print(f"   - Job Applications: {JobApplication.objects.count()}")
    print(f"   - Direct Hire Requests: {DirectHireRequest.objects.count()}")
    print(f"   - Messages: {Message.objects.count()}")
    print(f"   - Time Tracking: {TimeTracking.objects.count()}")
    print(f"   - Worker Activities: {WorkerActivity.objects.count()}")
    print(f"   - Saved Jobs: {SavedJob.objects.count()}")
    
    print()
    print("✅ Database cleanup complete!")
    print("📝 Users, worker profiles, categories, and system data preserved")
    print()

if __name__ == '__main__':
    try:
        clean_database()
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
