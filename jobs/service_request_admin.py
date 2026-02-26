"""
Admin registration for Service Request models
"""

from django.contrib import admin
from jobs.service_request_models import ServiceRequest, TimeTracking, WorkerActivity


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'client', 'category', 'status', 'urgency', 'assigned_worker', 'created_at']
    list_filter = ['status', 'urgency', 'category', 'created_at']
    search_fields = ['title', 'description', 'client__email', 'client__first_name', 'client__last_name']
    readonly_fields = ['created_at', 'updated_at', 'assigned_at', 'worker_response_at', 'work_started_at', 'work_completed_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'category', 'title', 'description')
        }),
        ('Location', {
            'fields': ('location', 'city')
        }),
        ('Scheduling', {
            'fields': ('preferred_date', 'preferred_time', 'estimated_duration_hours', 'urgency')
        }),
        ('Assignment', {
            'fields': ('status', 'assigned_worker', 'assigned_by', 'assigned_at', 'admin_notes')
        }),
        ('Worker Response', {
            'fields': ('worker_accepted', 'worker_response_at', 'worker_rejection_reason')
        }),
        ('Completion', {
            'fields': ('work_started_at', 'work_completed_at', 'completed_by_worker_at', 'completion_notes')
        }),
        ('Billing', {
            'fields': ('hourly_rate', 'total_hours_worked', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'category', 'assigned_worker', 'assigned_worker__user', 'assigned_by'
        )


@admin.register(TimeTracking)
class TimeTrackingAdmin(admin.ModelAdmin):
    list_display = ['id', 'worker', 'service_request', 'clock_in', 'clock_out', 'duration_hours', 'verified_by_client']
    list_filter = ['verified_by_client', 'clock_in', 'clock_out']
    search_fields = ['worker__user__email', 'service_request__title']
    readonly_fields = ['duration_hours', 'created_at', 'updated_at', 'verified_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('service_request', 'worker')
        }),
        ('Time Tracking', {
            'fields': ('clock_in', 'clock_out', 'duration_hours')
        }),
        ('Location', {
            'fields': ('clock_in_location', 'clock_out_location')
        }),
        ('Notes & Verification', {
            'fields': ('notes', 'verified_by_client', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'worker', 'worker__user', 'service_request'
        )


@admin.register(WorkerActivity)
class WorkerActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'worker', 'activity_type', 'service_request', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['worker__user__email', 'description', 'service_request__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('worker', 'service_request', 'activity_type')
        }),
        ('Details', {
            'fields': ('description', 'location', 'duration', 'amount_earned')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'worker', 'worker__user', 'service_request'
        )
