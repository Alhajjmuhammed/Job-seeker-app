"""
URL configuration for worker_connect project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .health_views import health_check, health_check_detailed, readiness_check, liveness_check
from jobs.service_request_urls import admin_urlpatterns, worker_urlpatterns, client_urlpatterns

# API Documentation Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Worker Connect API",
        default_version='v1',
        description="""
## Worker Connect API Documentation

Worker Connect is a platform connecting clients with workers for various services.

### Authentication
Most endpoints require authentication via Token. Include the token in the Authorization header:
```
Authorization: Token <your-token>
```

### Rate Limiting
- Login: 5 requests/minute
- Registration: 3 requests/minute  
- General API: 100 requests/hour (anonymous), 1000 requests/hour (authenticated)

### User Types
- **Worker**: Can browse jobs, apply for jobs, manage profile
- **Client**: Can post jobs, search workers, hire workers
        """,
        terms_of_service="https://workerconnect.com/terms/",
        contact=openapi.Contact(email="support@workerconnect.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Redirect admin login to custom system login
    path('admin/login/', RedirectView.as_view(pattern_name='accounts:login', query_string=True), name='admin_login_redirect'),
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='http_landing.html'), name='home'),
    
    # Health Check Endpoints (for monitoring and load balancers)
    path('api/health/', health_check, name='health_check'),
    path('api/health/detailed/', health_check_detailed, name='health_check_detailed'),
    path('api/health/ready/', readiness_check, name='readiness_check'),
    path('api/health/live/', liveness_check, name='liveness_check'),
    
    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/docs.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # API v1 endpoints (current version) - each app gets unique path
    path('api/v1/accounts/', include('accounts.api_urls')),
    path('api/v1/jobs/', include('jobs.api_urls')),
    path('api/v1/clients/', include(('clients.api_urls', 'clients'), namespace='clients_api_v1')),
    path('api/v1/workers/', include(('workers.api_urls', 'workers'), namespace='workers_api_v1')),
    path('api/v1/admin/', include('admin_panel.api_urls')),
    
    # Backward compatibility - support /api/ without version (mobile app)
    path('api/accounts/', include('accounts.api_urls')),
    path('api/', include('accounts.api_urls')),  # Direct routes for mobile (includes auth/ and notifications/)
    path('api/jobs/', include('jobs.api_urls')),
    path('api/clients/', include('clients.api_urls')),  # Uses original namespace clients_api_v2
    path('api/workers/', include('workers.api_urls')),  # Uses original namespace workers_api_v2
    
    # Search endpoints (consolidated)
    path('api/v1/search/', include('worker_connect.search_urls')),
    path('api/v1/search/jobs/', include(('jobs.search_urls', 'jobs'), namespace='job_search_v1')),
    path('api/jobs/search/', include(('jobs.search_urls', 'jobs'), namespace='job_search_mobile')),  # Mobile compatibility
    path('api/search/', include(('worker_connect.search_urls', 'wc'), namespace='wc_search_mobile')),  # Mobile compatibility
    
    # Messaging and chat (consolidated)
    path('api/messages/', include('jobs.messaging_urls')),  # Mobile and web compatibility
    path('api/v1/chat/', include('worker_connect.chat_urls')),
    
    # Worker-related endpoints (consolidated)
    path('api/v1/worker-availability/', include('workers.availability_urls')),
    path('api/v1/worker-earnings/', include('workers.earnings_urls')),
    path('api/v1/worker-badges/', include('workers.badge_urls')),
    path('api/v1/worker-portfolio/', include('workers.portfolio_urls')),
    
    # Job-related endpoints (consolidated)
    path('api/v1/job-recommendations/', include('jobs.recommendation_urls')),
    path('api/v1/job-skills/', include('jobs.skills_urls')),
    path('api/v1/job-completion/', include('jobs.completion_urls')),
    path('api/v1/job-reviews/', include('jobs.review_urls')),
    path('api/v1/job-categories/', include('jobs.category_urls')),
    path('api/v1/job-invoices/', include('jobs.invoice_urls')),
    path('api/v1/job-activity/', include('jobs.activity_urls')),
    
    # =========================================================================
    # NEW: Service Request System (Admin-Mediated Workflow)
    # =========================================================================
    path('api/v1/admin/', include(admin_urlpatterns)),
    path('api/v1/worker/', include(worker_urlpatterns)),
    path('api/v1/client/', include(client_urlpatterns)),
    
    # Payment system endpoints
    path('api/v1/payments/', include('worker_connect.payment_urls')),
    
    # Core system endpoints
    path('api/v1/gdpr/', include('accounts.gdpr_urls')),
    path('api/v1/notification-preferences/', include('accounts.notification_urls')),
    path('api/v1/admin-performance/', include('worker_connect.performance_urls')),
    
    # Core feature endpoints with mobile compatibility
    path('api/v1/config/', include(('worker_connect.config_urls', 'config'), namespace='wc_config_v1')),
    path('api/config/', include('worker_connect.config_urls')),  # Mobile compatibility - original namespace
    
    path('api/v1/support/', include(('worker_connect.support_urls', 'support'), namespace='wc_support_v1')),
    path('api/support/', include('worker_connect.support_urls')),  # Mobile compatibility - original namespace
    
    path('api/v1/notifications/', include(('worker_connect.notification_urls', 'notifications'), namespace='wc_notifications_v1')),
    path('api/notifications/', include('worker_connect.notification_urls')),  # Mobile compatibility - original namespace
    
    # Document verification (admin)
    # path('verification/', include('worker_connect.verification_urls')),
    
    # Web views
    path('accounts/', include('accounts.urls')),
    path('workers/', include('workers.urls')),
    path('clients/', include('clients.urls')),
    path('jobs/', include('jobs.urls')),
    path('dashboard/', include('admin_panel.urls')),
    
    # Service Request Web Interface (NEW)
    path('services/', include('jobs.service_request_web_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler400 = 'worker_connect.error_handlers.handler400'
handler403 = 'worker_connect.error_handlers.handler403'
handler404 = 'worker_connect.error_handlers.handler404'
handler500 = 'worker_connect.error_handlers.handler500'

# Customize admin site
admin.site.site_header = "Worker Connect Administration"
admin.site.site_title = "Worker Connect Admin"
admin.site.index_title = "Welcome to Worker Connect Admin Panel"

# Force admin to use custom login URL instead of Django's default
admin.site.login_url = '/accounts/login/'
