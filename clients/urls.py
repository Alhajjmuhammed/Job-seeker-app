from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('services/', views.browse_services, name='browse_services'),
    path('services/<int:category_id>/request/', views.request_service, name='request_service'),
    path('requests/', views.my_service_requests, name='my_service_requests'),
    path('requests/<int:request_id>/', views.service_request_detail, name='service_request_detail'),
    path('requests/<int:request_id>/cancel/', views.cancel_service_request, name='cancel_service_request'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
