"""Test script to verify worker image and modal setup"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.models import ServiceRequest, ServiceRequestAssignment

# Get service request 46
sr = ServiceRequest.objects.get(id=46)
print(f"Service Request: {sr.title}")

# Check assignments
assignments = ServiceRequestAssignment.objects.filter(service_request=sr)
print(f"\nAssignments: {assignments.count()}")

for assignment in assignments:
    worker = assignment.worker
    print(f"\nWorker: {worker.user.get_full_name()}")
    print(f"Status: {assignment.status}")
    
    if worker.profile_image:
        print(f"Profile Image URL: {worker.profile_image.url}")
        print(f"Profile Image Path: {worker.profile_image.path}")
        
        # Check if file exists
        if os.path.exists(worker.profile_image.path):
            file_size = os.path.getsize(worker.profile_image.path)
            print(f"File exists: YES ({file_size:,} bytes)")
        else:
            print("File exists: NO")
            
        # Generate the onclick JavaScript that would be in the template
        onclick_js = f"showWorkerImage('{worker.profile_image.url}', '{worker.user.get_full_name()}')"
        print(f"\nExpected onclick: {onclick_js}")
    else:
        print("No profile image")
