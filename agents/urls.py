from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('workers/', views.my_workers, name='workers'),
    path('workers/create/', views.create_worker, name='create_worker'),
    path('workers/<int:worker_id>/add/', views.add_worker, name='add_worker'),
    path('workers/<int:worker_id>/remove/', views.remove_worker, name='remove_worker'),
    path('profile/', views.profile, name='profile'),
]
