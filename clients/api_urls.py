from django.urls import path
from . import api_views

app_name = 'clients_api'

urlpatterns = [
    # Client profile
    path('profile/', api_views.client_profile, name='client_profile'),
    path('profile/update/', api_views.update_client_profile, name='update_client_profile'),
    
    # Statistics
    path('stats/', api_views.client_stats, name='client_stats'),
    
    # Jobs
    path('jobs/', api_views.client_jobs, name='client_jobs'),
    path('jobs/<int:job_id>/', api_views.client_job_detail, name='client_job_detail'),
    
    # Worker search and discovery
    path('workers/search/', api_views.search_workers, name='search_workers'),
    path('workers/featured/', api_views.featured_workers, name='featured_workers'),
    path('workers/<int:worker_id>/', api_views.worker_detail, name='worker_detail'),
    
    # Favorites
    path('workers/<int:worker_id>/favorite/', api_views.toggle_favorite, name='toggle_favorite'),
    path('workers/<int:worker_id>/rate/', api_views.rate_worker, name='rate_worker'),
    path('favorites/', api_views.favorites_list, name='favorites_list'),
    
    # Categories
    path('categories/', api_views.categories_list, name='categories_list'),
]
