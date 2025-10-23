from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('workers/verification/', views.worker_verification_list, name='worker_verification_list'),
    path('workers/verify/<int:worker_id>/', views.verify_worker, name='verify_worker'),
    path('documents/', views.document_verification_list, name='document_verification_list'),
    path('documents/verify/<int:doc_id>/', views.verify_document, name='verify_document'),
    path('categories/', views.category_list, name='category_list'),
    path('reports/', views.reports, name='reports'),
    
    # Job management URLs
    path('jobs/', views.job_management, name='job_management'),
    path('jobs/<int:job_id>/assign/', views.assign_worker, name='assign_worker'),
    
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
]
