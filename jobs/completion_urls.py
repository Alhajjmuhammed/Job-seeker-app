"""
URL routes for job completion and saved jobs.
"""

from django.urls import path
from . import completion_views

urlpatterns = [
    # Job completion workflow
    path('<int:job_id>/submit/', completion_views.submit_work, name='submit_work'),
    path('<int:job_id>/approve/', completion_views.approve_completion, name='approve_completion'),
    path('<int:job_id>/revision/', completion_views.request_revision, name='request_revision'),
    path('<int:job_id>/dispute/', completion_views.open_dispute, name='open_dispute'),
    path('<int:job_id>/resolve/', completion_views.resolve_dispute, name='resolve_dispute'),
    path('<int:job_id>/cancel/', completion_views.cancel_job, name='cancel_job'),
    path('<int:job_id>/timeline/', completion_views.job_timeline, name='job_timeline'),
    
    # Saved jobs
    path('<int:job_id>/save/', completion_views.save_job, name='save_job'),
    path('<int:job_id>/unsave/', completion_views.unsave_job, name='unsave_job'),
    path('<int:job_id>/is-saved/', completion_views.is_job_saved, name='is_job_saved'),
    path('saved/', completion_views.get_saved_jobs, name='get_saved_jobs'),
    path('saved/clear/', completion_views.clear_unavailable_saved, name='clear_unavailable_saved'),
]
