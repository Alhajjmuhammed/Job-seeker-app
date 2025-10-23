from django.contrib import admin
from .models import JobRequest, JobApplication, Message


@admin.register(JobRequest)
class JobRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'category', 'status', 'urgency', 'budget', 'created_at']
    list_filter = ['status', 'urgency', 'category', 'created_at']
    search_fields = ['title', 'description', 'client__username', 'location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['job', 'worker', 'status', 'proposed_rate', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job__title', 'worker__user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'subject', 'message']
    readonly_fields = ['created_at']
