from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('search/', views.search_workers, name='search_workers'),
    path('worker/<int:pk>/', views.worker_detail, name='worker_detail'),
    path('worker/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('worker/<int:pk>/rate/', views.rate_worker, name='rate_worker'),
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
