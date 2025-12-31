"""
URL routes for badges and verification.
"""

from django.urls import path
from . import badge_views

urlpatterns = [
    # Badge types
    path('types/', badge_views.get_available_badges, name='badge_types'),
    path('tiers/', badge_views.get_verification_tiers, name='verification_tiers'),
    
    # Worker badges
    path('my/', badge_views.get_my_badges, name='my_badges'),
    path('my/tier/', badge_views.get_my_tier, name='my_tier'),
    path('worker/<int:worker_id>/', badge_views.get_worker_badges, name='worker_badges'),
    
    # Apply for badge
    path('apply/', badge_views.apply_for_badge, name='apply_badge'),
    
    # Admin
    path('pending/', badge_views.pending_badge_applications, name='pending_badges'),
    path('<int:badge_id>/verify/', badge_views.verify_badge, name='verify_badge'),
]
