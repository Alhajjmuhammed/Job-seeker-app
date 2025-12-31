"""
URL routes for job recommendations.
"""

from django.urls import path
from . import recommendation_views

urlpatterns = [
    # Job recommendations for workers
    path('recommendations/', recommendation_views.get_job_recommendations, name='job_recommendations'),
    
    # Worker recommendations for clients
    path('recommendations/<int:job_id>/workers/', recommendation_views.get_worker_recommendations, name='worker_recommendations'),
    
    # Similar jobs
    path('similar/<int:job_id>/', recommendation_views.get_similar_jobs, name='similar_jobs'),
]
