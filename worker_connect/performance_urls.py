"""
URL routes for performance monitoring.
"""

from django.urls import path
from . import performance_views

urlpatterns = [
    path('summary/', performance_views.performance_summary, name='perf_summary'),
    path('endpoints/', performance_views.endpoint_stats, name='perf_endpoints'),
    path('queries/', performance_views.slow_queries, name='perf_queries'),
    path('errors/', performance_views.recent_errors, name='perf_errors'),
    path('clear/', performance_views.clear_metrics, name='perf_clear'),
    path('system/', performance_views.system_health, name='perf_system'),
]
