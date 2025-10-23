from django.urls import path
from . import views

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
    
    # Messaging
    path('inbox/', views.inbox, name='inbox'),
    path('message/send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('conversation/<int:user_id>/', views.conversation, name='conversation'),
    path('message/<int:pk>/', views.message_detail, name='message_detail'),
]
