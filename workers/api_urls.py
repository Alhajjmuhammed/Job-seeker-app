from django.urls import path
from . import api_views

app_name = 'workers_api'

urlpatterns = [
    path('profile/', api_views.worker_profile, name='worker_profile'),
    path('profile/update/', api_views.update_worker_profile, name='update_worker_profile'),
    path('profile/completion/', api_views.profile_completion, name='profile_completion'),
    path('availability/', api_views.update_worker_availability, name='update_worker_availability'),
    path('stats/', api_views.worker_stats, name='worker_stats'),
    path('direct-hire-requests/', api_views.direct_hire_requests, name='direct_hire_requests'),
    path('documents/upload/', api_views.upload_document, name='upload_document'),
    path('documents/', api_views.get_documents, name='get_documents'),
    path('documents/<int:document_id>/delete/', api_views.delete_document, name='delete_document'),
    path('categories/', api_views.get_categories, name='get_categories'),
    path('skills/', api_views.get_skills_by_category, name='get_skills_by_category'),
    path('experiences/', api_views.work_experiences, name='work_experiences'),
    path('experiences/<int:experience_id>/', api_views.work_experience_detail, name='work_experience_detail'),
    # Analytics and earnings endpoints
    path('analytics/', api_views.worker_analytics, name='worker_analytics'),
    path('earnings/breakdown/', api_views.earnings_breakdown, name='earnings_breakdown'),
    path('earnings/by-category/', api_views.earnings_by_category, name='earnings_by_category'),
    path('earnings/top-clients/', api_views.top_clients, name='top_clients'),
    path('earnings/payment-history/', api_views.payment_history, name='payment_history'),
    # Push notifications
    path('push-token/register/', api_views.register_push_token, name='register_push_token'),
]
