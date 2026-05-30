"""
URL routes for reviews.
"""

from django.urls import path
from . import review_views

urlpatterns = [
    # Create review
    path('', review_views.create_review, name='create_review'),
    
    # User reviews
    path('user/<int:user_id>/', review_views.get_user_reviews, name='user_reviews'),
    path('user/<int:user_id>/summary/', review_views.get_rating_summary, name='rating_summary'),
    
    # My reviews
    path('me/', review_views.get_my_reviews, name='my_reviews'),
    path('given/', review_views.get_reviews_given, name='reviews_given'),
    
    # Job reviews
    path('job/<int:job_id>/', review_views.get_job_reviews, name='job_reviews'),
    
    # Review actions
    path('<int:review_id>/respond/', review_views.respond_to_review, name='respond_review'),
    path('<int:review_id>/flag/', review_views.flag_review, name='flag_review'),
]
