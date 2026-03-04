from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'clients'

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('services/', views.browse_services, name='browse_services'),
    path('services/<int:category_id>/request/', views.request_service, name='request_service'),
    
    # Redirect old service request URLs to new ones
    path('requests/', RedirectView.as_view(pattern_name='service_requests_web:client_my_requests', permanent=True), name='my_service_requests'),
    path('requests/<int:pk>/', RedirectView.as_view(pattern_name='service_requests_web:client_request_detail', permanent=True), name='service_request_detail'),
    path('requests/<int:pk>/cancel/', RedirectView.as_view(pattern_name='service_requests_web:client_cancel_request', permanent=True), name='cancel_service_request'),
    
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
