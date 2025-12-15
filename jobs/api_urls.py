from django.urls import path
from .api_views import (
    worker_direct_hire_requests,
    accept_direct_hire_request,
    reject_direct_hire_request,
    worker_job_listings,
    worker_applications,
    apply_for_job,
    worker_stats,
)

urlpatterns = [
    # Worker endpoints
    path('worker/direct-hire-requests/', worker_direct_hire_requests, name='api_worker_direct_hire_requests'),
    path('worker/direct-hire-requests/<int:request_id>/accept/', accept_direct_hire_request, name='api_accept_direct_hire'),
    path('worker/direct-hire-requests/<int:request_id>/reject/', reject_direct_hire_request, name='api_reject_direct_hire'),
    path('worker/jobs/', worker_job_listings, name='api_worker_jobs'),
    path('worker/applications/', worker_applications, name='api_worker_applications'),
    path('worker/jobs/<int:job_id>/apply/', apply_for_job, name='api_apply_for_job'),
    path('worker/stats/', worker_stats, name='api_worker_stats'),
]
