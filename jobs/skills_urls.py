"""
URL routes for skills matching.
"""

from django.urls import path
from . import skills_views

urlpatterns = [
    # Skill matching
    path('match/', skills_views.match_skills, name='match_skills'),
    
    # Find matching workers for a job
    path('workers/<int:job_id>/', skills_views.find_matching_workers, name='find_matching_workers'),
    
    # Find matching jobs for worker
    path('jobs/', skills_views.find_matching_jobs, name='find_matching_jobs'),
    
    # Skill suggestions
    path('suggest/', skills_views.suggest_skills, name='suggest_skills'),
    
    # Skill categories (public)
    path('categories/', skills_views.get_skill_categories, name='skill_categories'),
]
