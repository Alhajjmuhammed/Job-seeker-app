from django.urls import path
from . import api_views, pricing_api

app_name = 'clients_api_v2'

urlpatterns = [
    # Root clients API endpoint
    path('', api_views.client_profile, name='api_clients_root'),
    
    # Client profile
    path('profile/', api_views.client_profile, name='client_profile'),
    path('profile/update/', api_views.update_client_profile, name='update_client_profile'),
    
    # Statistics
    path('stats/', api_views.client_stats, name='client_stats'),
    
    # Jobs
    path('jobs/', api_views.client_jobs, name='client_jobs'),
    path('jobs/<int:job_id>/', api_views.client_job_detail, name='client_job_detail'),
    
    # Service Categories (ONLY) - No worker access
    path('services/', api_views.services_list, name='services_list'),
    path('services/<int:category_id>/request/', api_views.request_service, name='request_service'),
    
    # Job Requests Management
    path('requests/', api_views.my_service_requests, name='my_service_requests'),
    path('requests/<int:request_id>/', api_views.service_request_detail, name='service_request_detail'),
    path('requests/<int:request_id>/cancel/', api_views.cancel_service_request, name='cancel_service_request'),
    path('requests/<int:request_id>/complete/', api_views.complete_service_request, name='complete_service_request'),
    path('requests/<int:request_id>/update/', api_views.update_service_request, name='update_service_request'),
    
    # Categories (for display purposes only)
    path('categories/', api_views.categories_list, name='categories_list'),
    
    # Favorites
    path('favorites/', api_views.favorites_list, name='favorites_list'),
    path('favorites/toggle/<int:worker_id>/', api_views.toggle_favorite, name='toggle_favorite'),
    
    # Pricing & Payment (NEW)
    path('calculate-price/', pricing_api.calculate_price, name='calculate_price'),
    path('process-payment/', pricing_api.process_fake_payment, name='process_payment'),
    path('category-pricing/', pricing_api.get_category_pricing, name='category_pricing'),
]
