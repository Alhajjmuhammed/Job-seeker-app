from django.urls import path
from . import messaging, reports

app_name = 'messaging'

urlpatterns = [
    # Messaging
    path('conversations/', messaging.get_conversations, name='get_conversations'),
    path('conversations/<int:job_id>/', messaging.get_messages, name='get_messages'),
    path('conversations/<int:job_id>/send/', messaging.send_message, name='send_message'),
    path('conversations/<int:job_id>/read/', messaging.mark_all_read, name='mark_all_read'),
    path('unread/', messaging.unread_count, name='unread_count'),
    
    # Reports
    path('reports/', reports.submit_report, name='submit_report'),
    path('reports/list/', reports.list_reports, name='list_reports'),
    path('reports/<int:report_id>/review/', reports.review_report, name='review_report'),
    path('reports/stats/', reports.report_statistics, name='report_statistics'),
]
