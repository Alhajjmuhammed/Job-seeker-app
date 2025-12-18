from django.urls import path
from . import api_views

app_name = 'workers_api'

urlpatterns = [
    path('profile/', api_views.worker_profile, name='worker_profile'),
    path('profile/update/', api_views.update_worker_profile, name='update_worker_profile'),
    path('availability/', api_views.update_worker_availability, name='update_worker_availability'),
    path('stats/', api_views.worker_stats, name='worker_stats'),
    path('direct-hire-requests/', api_views.direct_hire_requests, name='direct_hire_requests'),
]
