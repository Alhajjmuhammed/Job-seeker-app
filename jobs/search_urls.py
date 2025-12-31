from django.urls import path
from . import search

app_name = 'search'

urlpatterns = [
    path('', search.search_jobs, name='search_jobs'),
    path('workers/', search.search_workers, name='search_workers'),
    path('suggestions/', search.search_suggestions, name='search_suggestions'),
    path('filters/', search.get_filter_options, name='filter_options'),
]
