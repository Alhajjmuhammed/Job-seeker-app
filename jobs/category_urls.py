"""
URL routes for job categories.
"""

from django.urls import path
from . import category_views

app_name = 'job_categories'

urlpatterns = [
    path('', category_views.list_categories, name='list_categories'),
    path('popular/', category_views.popular_categories, name='popular_categories'),
    path('<int:category_id>/', category_views.get_category, name='get_category'),
    path('create/', category_views.create_category, name='create_category'),
    path('<int:category_id>/update/', category_views.update_category, name='update_category'),
    path('<int:category_id>/delete/', category_views.delete_category, name='delete_category'),
]
