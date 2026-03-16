"""
Quick diagnostic script to check worker profile image URLs
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from django.conf import settings

# Get the service request
request_id = 46
try:
    service_request = ServiceRequest.objects.get(id=request_id)
    print(f"\n{'='*80}")
    print(f"SERVICE REQUEST #{request_id} DIAGNOSTIC")
    print(f"{'='*80}\n")
    
    print(f"Title: {service_request.title}")
    print(f"Status: {service_request.status}")
    print(f"Workers Needed: {service_request.workers_needed}")
    
    # Get assignments
    assignments = service_request.assignments.all().select_related('worker', 'worker__user')
    print(f"\nTotal Assignments: {assignments.count()}")
    
    for idx, assignment in enumerate(assignments, 1):
        print(f"\n{'─'*80}")
        print(f"ASSIGNMENT #{idx}")
        print(f"{'─'*80}")
        print(f"  Worker: {assignment.worker.user.get_full_name()}")
        print(f"  Status: {assignment.status}")
        print(f"  Assignment Number: {assignment.assignment_number}")
        print(f"  Email: {assignment.worker.user.email}")
        
        # Check profile image
        if assignment.worker.profile_image:
            print(f"  ✅ Has profile_image: {assignment.worker.profile_image.name}")
            print(f"  URL: {assignment.worker.profile_image.url}")
            
            # Check if file exists
            full_path = os.path.join(settings.MEDIA_ROOT, assignment.worker.profile_image.name)
            if os.path.exists(full_path):
                print(f"  ✅ File exists at: {full_path}")
                file_size = os.path.getsize(full_path)
                print(f"  File size: {file_size:,} bytes")
            else:
                print(f"  ❌ File NOT found at: {full_path}")
        else:
            print(f"  ❌ No profile_image set")
        
        # Check user profile picture fallback
        if hasattr(assignment.worker.user, 'profile_picture') and assignment.worker.user.profile_picture:
            print(f"  ℹ️  Has user.profile_picture: {assignment.worker.user.profile_picture.name}")
        else:
            print(f"  ℹ️  No user.profile_picture fallback")
    
    # Check media configuration
    print(f"\n{'='*80}")
    print(f"MEDIA CONFIGURATION")
    print(f"{'='*80}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"MEDIA_ROOT exists: {os.path.exists(settings.MEDIA_ROOT)}")
    
    # Filter accepted assignments (what client sees)
    accepted_assignments = assignments.filter(status__in=['accepted', 'in_progress', 'completed'])
    print(f"\n{'='*80}")
    print(f"CLIENT VIEW (Accepted/In Progress/Completed only)")
    print(f"{'='*80}")
    print(f"Visible to client: {accepted_assignments.count()} workers")
    
    for idx, assignment in enumerate(accepted_assignments, 1):
        print(f"  {idx}. {assignment.worker.user.get_full_name()} - Status: {assignment.status}")
        if assignment.worker.profile_image:
            print(f"     ✅ Image: {assignment.worker.profile_image.url}")
        else:
            print(f"     ❌ No image")
    
    print(f"\n{'='*80}\n")
    
except ServiceRequest.DoesNotExist:
    print(f"\n❌ Service Request #{request_id} not found!\n")
except Exception as e:
    print(f"\n❌ Error: {str(e)}\n")
    import traceback
    traceback.print_exc()
