"""
URL patterns for Web Interface - Service Requests
"""

from django.urls import path
from clients import service_request_web_views as client_web
from workers import service_request_web_views as worker_web

app_name = 'service_requests_web'

urlpatterns = [
    # =========================================================================
    # CLIENT WEB INTERFACE
    # =========================================================================
    path('client/dashboard/', client_web.client_web_dashboard, name='client_dashboard'),
    path('client/request-service/', client_web.client_web_request_service, name='client_request_service'),
    path('client/my-requests/', client_web.client_web_my_requests, name='client_my_requests'),
    path('client/request/<int:pk>/', client_web.client_web_request_detail, name='client_request_detail'),
    path('client/request/<int:pk>/cancel/', client_web.client_web_cancel_request, name='client_cancel_request'),
    path('client/request/<int:pk>/rate/', client_web.client_web_rate_worker, name='client_rate_worker'),
    path('client/history/', client_web.client_web_history, name='client_history'),
    
    # =========================================================================
    # WORKER WEB INTERFACE
    # =========================================================================
    path('worker/dashboard/', worker_web.worker_web_dashboard, name='worker_dashboard'),
    path('worker/assignments/', worker_web.worker_web_assignments, name='worker_assignments'),
    path('worker/pending/', worker_web.worker_web_pending_assignments, name='worker_pending'),
    path('worker/assignment/<int:pk>/', worker_web.worker_web_assignment_detail, name='worker_assignment_detail'),
    path('worker/assignment/<int:pk>/respond/', worker_web.worker_web_respond_assignment, name='worker_respond'),
    path('worker/assignment/<int:pk>/clock-in/', worker_web.worker_web_clock_in, name='worker_clock_in'),
    path('worker/assignment/<int:pk>/clock-out/', worker_web.worker_web_clock_out, name='worker_clock_out'),
    path('worker/assignment/<int:pk>/complete/', worker_web.worker_web_complete_service, name='worker_complete'),
    path('worker/activity/', worker_web.worker_web_activity, name='worker_activity'),
]
