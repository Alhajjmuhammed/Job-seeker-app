from django.contrib import admin
from .models import ClientProfile, Rating, Favorite


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'city', 'total_jobs_posted', 'total_spent', 'created_at']
    list_filter = ['city', 'created_at']
    search_fields = ['user__username', 'user__email', 'company_name', 'city']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['client', 'worker', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['client__username', 'worker__user__username']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['client', 'worker', 'created_at']
    list_filter = ['created_at']
    search_fields = ['client__username', 'worker__user__username']
