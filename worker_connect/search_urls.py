from django.urls import path
from . import search_views

app_name = 'wc_search'

urlpatterns = [
    path('', search_views.general_search, name='general_search'),  # Root search endpoint
    path('jobs/', search_views.search_jobs, name='search_jobs'),
    path('workers/', search_views.search_workers, name='search_workers'),
    path('filters/', search_views.search_filters, name='search_filters'),
]