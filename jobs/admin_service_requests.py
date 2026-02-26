"""
Quick integration script to register service request models
Add this to your jobs/admin.py file
"""

# Import the admin registrations
from jobs.service_request_admin import ServiceRequestAdmin, TimeTrackingAdmin, WorkerActivityAdmin

# Models are already registered via decorators in service_request_admin.py
# No additional code needed - just import the file

# Optional: If you want to customize admin display further, you can override here
