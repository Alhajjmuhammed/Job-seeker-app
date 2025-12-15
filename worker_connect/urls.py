"""
URL configuration for worker_connect project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('api/', include('accounts.api_urls')),  # Auth API endpoints
    path('api/', include('jobs.api_urls')),  # Jobs API endpoints
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

# Customize admin site
admin.site.site_header = "Worker Connect Administration"
admin.site.site_title = "Worker Connect Admin"
admin.site.index_title = "Welcome to Worker Connect Admin Panel"
