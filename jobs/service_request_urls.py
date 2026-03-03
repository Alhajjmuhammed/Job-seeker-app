"""
URL patterns for Service Request API
"""

from django.urls import path
from admin_panel import service_request_views as admin_views
from workers import service_request_worker_views as worker_views
from clients import service_request_client_views as client_views
from clients import pricing_api

# Admin URLs - prefix: /api/v1/admin/
admin_urlpatterns = [
    path('service-requests/', admin_views.admin_service_requests, name='admin_service_requests'),
    path('service-requests/<int:pk>/', admin_views.admin_service_request_detail, name='admin_service_request_detail'),
    path('service-requests/<int:pk>/assign/', admin_views.admin_assign_worker, name='admin_assign_worker'),
    path('service-requests/<int:pk>/reassign/', admin_views.admin_reassign_worker, name='admin_reassign_worker'),
    path('service-requests/dashboard/', admin_views.admin_dashboard_stats, name='admin_service_dashboard_stats'),
    path('service-requests/workers/', admin_views.admin_available_workers, name='admin_available_workers'),
]

# Worker URLs - prefix: /api/v1/worker/
worker_urlpatterns = [
    path('service-requests/', worker_views.worker_assigned_services, name='worker_assigned_services'),
    path('service-requests/pending/', worker_views.worker_pending_assignments, name='worker_pending_assignments'),
    path('service-requests/current/', worker_views.worker_current_assignment, name='worker_current_assignment'),
    path('service-requests/<int:pk>/respond/', worker_views.worker_respond_to_assignment, name='worker_respond_assignment'),
    path('service-requests/<int:pk>/clock-in/', worker_views.worker_clock_in, name='worker_clock_in'),
    path('service-requests/<int:pk>/clock-out/', worker_views.worker_clock_out, name='worker_clock_out'),
    path('service-requests/<int:pk>/complete/', worker_views.worker_complete_service, name='worker_complete_service'),
    path('activity/', worker_views.worker_activity_history, name='worker_activity'),
    path('statistics/', worker_views.worker_statistics, name='worker_service_statistics'),
]

# Client URLs - prefix: /api/v1/client/
client_urlpatterns = [
    path('categories/', client_views.client_categories, name='client_categories'),
    
    # Pricing & Payment APIs
    path('calculate-price/', pricing_api.calculate_price, name='calculate_price'),
    path('process-payment/', pricing_api.process_fake_payment, name='process_payment'),
    path('category-pricing/', pricing_api.get_category_pricing, name='category_pricing'),
    
    # Service Requests
    path('service-requests/create/', client_views.client_create_service_request, name='client_create_service'),
    path('service-requests/', client_views.client_service_requests, name='client_service_requests'),
    path('service-requests/<int:pk>/', client_views.client_service_request_detail, name='client_service_detail'),
    path('service-requests/<int:pk>/update/', client_views.client_update_request, name='client_update_request'),
    path('service-requests/<int:pk>/cancel/', client_views.client_cancel_request, name='client_cancel_request'),
    path('service-requests/pending/', client_views.client_pending_requests, name='client_pending'),
    path('service-requests/in-progress/', client_views.client_in_progress_requests, name='client_in_progress'),
    path('service-requests/completed/', client_views.client_completed_requests, name='client_completed'),
    path('statistics/', client_views.client_statistics, name='client_service_statistics'),
]

# Default (for compatibility)
urlpatterns = admin_urlpatterns + worker_urlpatterns + client_urlpatterns
