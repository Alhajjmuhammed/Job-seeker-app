from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('workers/verification/', views.worker_verification_list, name='worker_verification_list'),
    path('workers/verify/<int:worker_id>/', views.verify_worker, name='verify_worker'),
    path('workers/<int:worker_id>/rate/', views.rate_worker, name='rate_worker'),
    path('workers/<int:worker_id>/ratings/', views.worker_ratings, name='worker_ratings'),
    path('documents/', views.document_verification_list, name='document_verification_list'),
    path('documents/verify/<int:doc_id>/', views.verify_document, name='verify_document'),
    path('categories/', views.category_list, name='category_list'),
    path('reports/', views.reports, name='reports'),
    
    # Job management URLs (legacy view for stats only)
    path('jobs/', views.job_management, name='job_management'),
    
    # Service Request management URLs
    path('service-requests/', views.service_request_list, name='service_request_list'),
    path('service-requests/<int:request_id>/', views.service_request_detail, name='service_request_detail'),
    path('service-requests/<int:request_id>/workers/', views.view_request_workers, name='view_request_workers'),
    path('service-requests/<int:request_id>/assign/', views.assign_worker_to_request, name='assign_worker_to_request'),
    path('service-requests/<int:request_id>/unassign/<int:assignment_id>/', views.unassign_worker_from_request, name='unassign_worker'),
    path('service-requests/<int:request_id>/verify-payment/', views.verify_payment, name='verify_payment'),
    
    # Export URLs
    path('reports/export/csv/', views.export_reports_csv, name='export_reports_csv'),
    path('reports/export/excel/', views.export_reports_excel, name='export_reports_excel'),
    path('reports/export/pdf/', views.export_reports_pdf, name='export_reports_pdf'),
    
    # User management URLs
    path('users/', views.manage_users, name='manage_users'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('system-overview/', views.system_overview, name='system_overview'),

    # Agent management URLs
    path('agents/', views.agent_list, name='agent_list'),
    path('agents/<int:agent_id>/', views.agent_detail, name='agent_detail'),
    path('agents/<int:agent_id>/approve/', views.approve_agent, name='approve_agent'),
    path('agents/<int:agent_id>/reject/', views.reject_agent, name='reject_agent'),
    path('agents/<int:agent_id>/commission/', views.update_agent_commission, name='update_agent_commission'),
    path('workers/<int:worker_id>/reassign-agent/', views.reassign_worker_agent, name='reassign_worker_agent'),
]
