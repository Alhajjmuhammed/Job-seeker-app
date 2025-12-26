from django.urls import path
from . import views
from . import api_messages

app_name = 'jobs'

urlpatterns = [
    # Job requests
    path('', views.job_list, name='job_list'),
    path('<int:pk>/', views.job_detail, name='job_detail'),
    path('create/', views.job_create, name='job_create'),
    path('<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('<int:pk>/delete/', views.job_delete, name='job_delete'),
    path('<int:pk>/close/', views.job_close, name='job_close'),
    
    # Job applications
    path('<int:pk>/apply/', views.apply_for_job, name='apply_for_job'),
    path('applications/', views.my_applications, name='my_applications'),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('application/<int:pk>/accept/', views.accept_application, name='accept_application'),
    path('application/<int:pk>/reject/', views.reject_application, name='reject_application'),
    
    # Messaging (Traditional Views)
    path('inbox/', views.inbox, name='inbox'),
    path('message/send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('conversation/<int:user_id>/', views.conversation, name='conversation'),
    path('message/<int:pk>/', views.message_detail, name='message_detail'),
    
    # Messaging API (for React Native)
    path('api/messages/conversations/', api_messages.get_conversations, name='api_conversations'),
    path('api/messages/<int:user_id>/', api_messages.get_messages, name='api_messages'),
    path('api/messages/send/', api_messages.send_message_api, name='api_send_message'),
    path('api/messages/unread/', api_messages.get_unread_count, name='api_unread_count'),
    path('api/messages/<int:message_id>/read/', api_messages.mark_as_read, name='api_mark_read'),
    path('api/messages/search-users/', api_messages.search_users, name='api_search_users'),
    
    # Direct Hire / On-Demand Booking
    path('direct-hire/request/<int:worker_id>/', views.request_worker_directly, name='request_worker_directly'),
    path('direct-hire/<int:pk>/', views.direct_hire_detail, name='direct_hire_detail'),
    path('direct-hire/<int:pk>/accept/', views.worker_accept_direct_hire, name='worker_accept_direct_hire'),
    path('direct-hire/<int:pk>/reject/', views.worker_reject_direct_hire, name='worker_reject_direct_hire'),
    path('direct-hire/<int:pk>/complete/', views.complete_direct_hire, name='complete_direct_hire'),
    path('direct-hires/', views.my_direct_hire_requests, name='my_direct_hire_requests'),
]
