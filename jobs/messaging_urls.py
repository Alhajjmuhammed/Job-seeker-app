from django.urls import path
from . import api_messages, reports

app_name = 'jobs_messaging'

urlpatterns = [
    # Messaging (using api_messages for mobile compatibility)
    path('conversations/', api_messages.get_conversations, name='get_conversations'),
    path('<int:user_id>/', api_messages.get_messages, name='get_messages'),  # Direct path for mobile
    path('send/', api_messages.send_message_api, name='send_message'),
    path('unread/', api_messages.get_unread_count, name='unread_count'),
    path('<int:message_id>/read/', api_messages.mark_as_read, name='mark_as_read'),
    path('search-users/', api_messages.search_users, name='search_users'),
    
    # Reports
    path('reports/', reports.submit_report, name='submit_report'),
    path('reports/list/', reports.list_reports, name='list_reports'),
    path('reports/<int:report_id>/review/', reports.review_report, name='review_report'),
    path('reports/stats/', reports.report_statistics, name='report_statistics'),
]
