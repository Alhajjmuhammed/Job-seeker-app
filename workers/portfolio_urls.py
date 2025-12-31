"""
URL routes for worker portfolio.
"""

from django.urls import path
from . import portfolio_views

app_name = 'portfolio'

urlpatterns = [
    # Worker's own portfolio
    path('my/', portfolio_views.get_my_portfolio, name='get_my_portfolio'),
    path('add/', portfolio_views.add_portfolio_item, name='add_portfolio_item'),
    path('<int:item_id>/update/', portfolio_views.update_portfolio_item, name='update_portfolio_item'),
    path('<int:item_id>/delete/', portfolio_views.delete_portfolio_item, name='delete_portfolio_item'),
    path('reorder/', portfolio_views.reorder_portfolio, name='reorder_portfolio'),
    path('<int:item_id>/featured/', portfolio_views.toggle_featured, name='toggle_featured'),
    
    # Public portfolio views
    path('worker/<int:worker_id>/', portfolio_views.get_worker_portfolio, name='get_worker_portfolio'),
    path('worker/<int:worker_id>/featured/', portfolio_views.get_featured_portfolio, name='get_featured_portfolio'),
]
