"""
URL routes for worker earnings.
"""

from django.urls import path
from . import earnings_views

urlpatterns = [
    path('summary/', earnings_views.earnings_summary, name='earnings_summary'),
    path('breakdown/', earnings_views.earnings_breakdown, name='earnings_breakdown'),
    path('categories/', earnings_views.earnings_by_category, name='earnings_categories'),
    path('clients/', earnings_views.top_clients, name='earnings_clients'),
    path('tax/', earnings_views.tax_estimate, name='earnings_tax'),
    path('history/', earnings_views.payment_history, name='earnings_history'),
]
