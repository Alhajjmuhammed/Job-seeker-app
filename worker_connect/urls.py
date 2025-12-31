"""
URL configuration for worker_connect project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .health_views import health_check, health_check_detailed, readiness_check, liveness_check

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
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Health Check Endpoints (for monitoring and load balancers)
    path('api/health/', health_check, name='health_check'),
    path('api/health/detailed/', health_check_detailed, name='health_check_detailed'),
    path('api/health/ready/', readiness_check, name='readiness_check'),
    path('api/health/live/', liveness_check, name='liveness_check'),
    
    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/docs.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # API v1 endpoints (current version)
    path('api/v1/', include('accounts.api_urls')),
    path('api/v1/', include('jobs.api_urls')),
    path('api/v1/client/', include('clients.api_urls')),
    path('api/v1/workers/', include('workers.api_urls')),
    path('api/v1/admin/', include('admin_panel.api_urls')),
    
    # Backward compatibility - support /api/ without version (mobile app)
    path('api/', include('accounts.api_urls')),
    path('api/', include('jobs.api_urls')),
    path('api/client/', include('clients.api_urls')),
    path('api/workers/', include('workers.api_urls')),
    
    # Search endpoints
    path('api/v1/search/jobs/', include('jobs.search_urls'))
,
    
    # Messaging and reports
    path('api/v1/messaging/', include('jobs.messaging_urls')),
    
    # Worker availability
    path('api/v1/workers/', include('workers.availability_urls')),
    
    # Worker earnings
    path('api/v1/earnings/', include('workers.earnings_urls')),
    
    # Job recommendations
    path('api/v1/jobs/', include('jobs.recommendation_urls')),
    
    # Skills matching
    path('api/v1/skills/', include('jobs.skills_urls')),
    
    # Job completion workflow
    path('api/v1/jobs/', include('jobs.completion_urls')),
    
    # GDPR endpoints
    path('api/v1/gdpr/', include('accounts.gdpr_urls')),
    
    # Notification preferences
    path('api/v1/notifications/preferences/', include('accounts.notification_urls')),
    
    # Performance monitoring (admin)
    path('api/v1/admin/performance/', include('worker_connect.performance_urls')),
    
    # App configuration endpoints
    path('api/v1/config/', include('worker_connect.config_urls')),
    
    # Review and rating system
    path('api/v1/reviews/', include('jobs.review_urls')),
    
    # Worker badges and verification
    path('api/v1/badges/', include('workers.badge_urls')),
    
    # Job categories
    path('api/v1/categories/', include('jobs.category_urls')),
    
    # Worker portfolio
    path('api/v1/portfolio/', include('workers.portfolio_urls')),
    
    # Invoice management
    path('api/v1/invoices/', include('jobs.invoice_urls')),
    
    # Activity feed
    path('api/v1/activity/', include('jobs.activity_urls')),
    
    # Web views
    path('accounts/', include('accounts.urls')),
    path('workers/', include('workers.urls')),
    path('clients/', include('clients.urls')),
    path('jobs/', include('jobs.urls')),
    path('dashboard/', include('admin_panel.urls')),
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
