from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('dashboard/', views.worker_dashboard, name='dashboard'),
    path('profile/setup/', views.profile_setup, name='profile_setup'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/image/upload/', views.profile_image_upload, name='profile_image_upload'),
    path('profile/image/remove/', views.profile_image_remove, name='profile_image_remove'),
    path('profile/<int:pk>/', views.worker_public_profile, name='public_profile'),
    
    # Documents
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    
    # Experience
    path('experience/', views.experience_list, name='experience_list'),
    path('experience/add/', views.experience_add, name='experience_add'),
    path('experience/<int:pk>/edit/', views.experience_edit, name='experience_edit'),
    path('experience/<int:pk>/delete/', views.experience_delete, name='experience_delete'),
    
    # Custom Skills & Categories
    path('custom-skills/add/', views.custom_skill_add, name='custom_skill_add'),
    path('custom-skills/<int:pk>/delete/', views.custom_skill_delete, name='custom_skill_delete'),
    path('custom-categories/add/', views.custom_category_add, name='custom_category_add'),
    path('custom-categories/<int:pk>/delete/', views.custom_category_delete, name='custom_category_delete'),
]
