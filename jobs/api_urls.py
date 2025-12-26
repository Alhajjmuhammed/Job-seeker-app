from django.urls import path
from .api_views import (
    worker_direct_hire_requests,
    accept_direct_hire_request,
    reject_direct_hire_request,
    worker_job_listings,
    worker_applications,
    apply_for_job,
    worker_stats,
    client_jobs,
    client_job_detail,
    client_job_applications,
    accept_application,
    reject_application,
    browse_jobs,
)
from . import api_messages

urlpatterns = [
    # Messaging API
    path('messages/conversations/', api_messages.get_conversations, name='api_conversations'),
    path('messages/<int:user_id>/', api_messages.get_messages, name='api_messages'),
    path('messages/send/', api_messages.send_message_api, name='api_send_message'),
    path('messages/unread/', api_messages.get_unread_count, name='api_unread_count'),
    path('messages/<int:message_id>/read/', api_messages.mark_as_read, name='api_mark_read'),
    path('messages/search-users/', api_messages.search_users, name='api_search_users'),
    
    # Worker endpoints
    path('worker/direct-hire-requests/', worker_direct_hire_requests, name='api_worker_direct_hire_requests'),
    path('worker/direct-hire-requests/<int:request_id>/accept/', accept_direct_hire_request, name='api_accept_direct_hire'),
    path('worker/direct-hire-requests/<int:request_id>/reject/', reject_direct_hire_request, name='api_reject_direct_hire'),
    path('worker/jobs/', worker_job_listings, name='api_worker_jobs'),
    path('worker/applications/', worker_applications, name='api_worker_applications'),
    path('worker/jobs/<int:job_id>/apply/', apply_for_job, name='api_apply_for_job'),
    path('worker/stats/', worker_stats, name='api_worker_stats'),
    
    # Client endpoints
    path('client/jobs/', client_jobs, name='api_client_jobs'),
    path('client/jobs/<int:job_id>/', client_job_detail, name='api_client_job_detail'),
    path('client/jobs/<int:job_id>/applications/', client_job_applications, name='api_client_job_applications'),
    path('client/applications/<int:application_id>/accept/', accept_application, name='api_accept_application'),
    path('client/applications/<int:application_id>/reject/', reject_application, name='api_reject_application'),
    
    # Common endpoints
    path('jobs/browse/', browse_jobs, name='api_browse_jobs'),
]
