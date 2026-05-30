from django.urls import path
from . import api_views
from . import bulk_views

app_name = 'admin_api'

urlpatterns = [
    # Dashboard analytics
    path('analytics/overview/', api_views.dashboard_overview, name='dashboard_overview'),
    path('analytics/users/growth/', api_views.user_growth_chart, name='user_growth'),
    path('analytics/jobs/', api_views.job_statistics, name='job_statistics'),
    path('analytics/applications/', api_views.application_statistics, name='application_statistics'),
    path('analytics/workers/', api_views.worker_statistics, name='worker_statistics'),
    path('analytics/activity/', api_views.recent_activity, name='recent_activity'),
    
    # Bulk actions
    path('bulk/users/', bulk_views.bulk_user_action, name='bulk_user_action'),
    path('bulk/workers/', bulk_views.bulk_worker_action, name='bulk_worker_action'),
    path('bulk/jobs/', bulk_views.bulk_job_action, name='bulk_job_action'),
    path('bulk/applications/', bulk_views.bulk_application_action, name='bulk_application_action'),
    path('bulk/notifications/', bulk_views.bulk_send_notification, name='bulk_notification'),
    path('bulk/export/', bulk_views.bulk_export_users, name='bulk_export'),
]
