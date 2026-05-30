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
    actions = ['bulk_mark_pending', 'bulk_mark_in_progress', 'bulk_mark_completed', 'bulk_mark_cancelled', 
               'bulk_send_reminder', 'bulk_verify_payment', 'bulk_assign_worker']
    
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
    
    # ========================================================================
    # BULK ACTIONS
    # ========================================================================
    
    def bulk_mark_pending(self, request, queryset):
        """Bulk mark service requests as pending"""
        count = queryset.update(status='pending')
        self.message_user(request, f"{count} service request(s) marked as pending.")
    bulk_mark_pending.short_description = "✅ Mark as Pending"
    
    def bulk_mark_in_progress(self, request, queryset):
        """Bulk mark service requests as in progress"""
        count = 0
        for sr in queryset:
            if sr.assigned_worker:
                sr.status = 'in_progress'
                sr.save()
                count += 1
        self.message_user(request, f"{count} service request(s) marked as in progress. (Only assigned requests)")
    bulk_mark_in_progress.short_description = "▶️ Mark as In Progress"
    
    def bulk_mark_completed(self, request, queryset):
        """Bulk mark service requests as completed"""
        from django.utils import timezone
        count = 0
        for sr in queryset:
            if sr.status in ['in_progress', 'assigned']:
                sr.status = 'completed'
                sr.work_completed_at = timezone.now()
                sr.save()
                
                # Create activity record
                if sr.assigned_worker:
                    WorkerActivity.objects.create(
                        worker=sr.assigned_worker,
                        service_request=sr,
                        activity_type='completed',
                        description=f'Service request "{sr.title}" marked as completed by admin'
                    )
                count += 1
        self.message_user(request, f"{count} service request(s) marked as completed.")
    bulk_mark_completed.short_description = "✅ Mark as Completed"
    
    def bulk_mark_cancelled(self, request, queryset):
        """Bulk cancel service requests"""
        count = queryset.filter(status__in=['pending', 'assigned']).update(status='cancelled')
        self.message_user(request, f"{count} service request(s) cancelled. (Only pending/assigned)")
    bulk_mark_cancelled.short_description = "❌ Cancel Requests"
    
    def bulk_send_reminder(self, request, queryset):
        """Send reminder notifications to clients/workers"""
        from worker_connect.notification_helpers import notify_system_alert
        count = 0
        for sr in queryset:
            if sr.status == 'pending':
                # Remind client
                notify_system_alert(
                    sr.client,
                    'Pending Service Request',
                    f'Your service request "{sr.title}" is awaiting worker assignment.'
                )
                count += 1
            elif sr.status == 'assigned' and sr.assigned_worker:
                # Remind worker
                notify_system_alert(
                    sr.assigned_worker.user,
                    'Action Required',
                    f'Please respond to service request "{sr.title}".'
                )
                count += 1
            elif sr.status == 'in_progress' and sr.assigned_worker:
                # Remind worker to complete
                notify_system_alert(
                    sr.assigned_worker.user,
                    'Service In Progress',
                    f'Don\'t forget to complete service request "{sr.title}".'
                )
                count += 1
        self.message_user(request, f"Sent {count} reminder notification(s).")
    bulk_send_reminder.short_description = "🔔 Send Reminders"
    
    def bulk_verify_payment(self, request, queryset):
        """Bulk verify payment screenshots"""
        from django.utils import timezone
        count = 0
        for sr in queryset:
            if sr.payment_screenshot and not sr.payment_verified:
                sr.payment_verified = True
                sr.payment_verified_by = request.user
                sr.payment_verified_at = timezone.now()
                sr.save()
                
                # Notify client
                from worker_connect.notification_helpers import notify_system_alert
                notify_system_alert(
                    sr.client,
                    'Payment Verified',
                    f'Your payment for "{sr.title}" has been verified.'
                )
                count += 1
        self.message_user(request, f"{count} payment(s) verified.")
    bulk_verify_payment.short_description = "💰 Verify Payments"
    
    def bulk_assign_worker(self, request, queryset):
        """Bulk assign worker (if only one worker available)"""
        from workers.models import WorkerProfile
        
        count = 0
        skipped = 0
        for sr in queryset.filter(status='pending', assigned_worker__isnull=True):
            # Find best matching worker
            matching_workers = WorkerProfile.objects.filter(
                categories=sr.category,
                verification_status='verified',
                availability='available'
            )
            
            if matching_workers.count() == 1:
                # Only auto-assign if exactly one worker matches
                worker = matching_workers.first()
                sr.assigned_worker = worker
                sr.assigned_by = request.user
                sr.status = 'assigned'
                from django.utils import timezone
                sr.assigned_at = timezone.now()
                sr.save()
                
                # Create activity
                WorkerActivity.objects.create(
                    worker=worker,
                    service_request=sr,
                    activity_type='assigned',
                    description=f'Auto-assigned to service request "{sr.title}"'
                )
                
                # Notify worker
                from worker_connect.notification_helpers import notify_system_alert
                notify_system_alert(
                    worker.user,
                    'New Assignment',
                    f'You have been assigned to service request "{sr.title}".'
                )
                count += 1
            else:
                skipped += 1
        
        if count > 0:
            self.message_user(request, f"{count} request(s) auto-assigned.")
        if skipped > 0:
            self.message_user(request, f"{skipped} request(s) skipped (no matching worker or multiple matches).", level='warning')
    bulk_assign_worker.short_description = "👤 Auto-Assign Worker"


@admin.register(TimeTracking)
class TimeTrackingAdmin(admin.ModelAdmin):
    list_display = ['id', 'worker', 'service_request', 'clock_in', 'clock_out', 'duration_hours', 'verified_by_client']
    list_filter = ['verified_by_client', 'clock_in', 'clock_out']
    search_fields = ['worker__user__email', 'service_request__title']
    readonly_fields = ['duration_hours', 'created_at', 'updated_at', 'verified_at']
    actions = ['bulk_verify_time', 'bulk_unverify_time']
    
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
    
    # Bulk actions for Time Tracking
    def bulk_verify_time(self, request, queryset):
        """Bulk verify time tracking entries"""
        from django.utils import timezone
        count = 0
        for entry in queryset.filter(verified_by_client=False):
            entry.verified_by_client = True
            entry.verified_at = timezone.now()
            entry.save()
            count += 1
        self.message_user(request, f"{count} time tracking entry(ies) verified.")
    bulk_verify_time.short_description = "✅ Verify Time Entries"
    
    def bulk_unverify_time(self, request, queryset):
        """Bulk unverify time tracking entries"""
        count = queryset.filter(verified_by_client=True).update(verified_by_client=False, verified_at=None)
        self.message_user(request, f"{count} time tracking entry(ies) unverified.")
    bulk_unverify_time.short_description = "❌ Unverify Time Entries"


@admin.register(WorkerActivity)
class WorkerActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'worker', 'activity_type', 'service_request', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['worker__user__email', 'description', 'service_request__title']
    readonly_fields = ['created_at']
    actions = ['bulk_delete_activities', 'bulk_export_activities']
    
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
    
    # Bulk actions for Worker Activity
    def bulk_delete_activities(self, request, queryset):
        """Bulk delete activity entries"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} activity entry(ies) deleted.")
    bulk_delete_activities.short_description = "🗑️ Delete Activities"
    
    def bulk_export_activities(self, request, queryset):
        """Export activities to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="worker_activities.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Worker', 'Activity Type', 'Service Request', 'Description', 'Date', 'Duration', 'Amount'])
        
        for activity in queryset:
            writer.writerow([
                activity.id,
                activity.worker.user.get_full_name(),
                activity.activity_type,
                activity.service_request.title if activity.service_request else 'N/A',
                activity.description,
                activity.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                activity.duration or 'N/A',
                activity.amount_earned or '0.00'
            ])
        
        return response
    bulk_export_activities.short_description = "📊 Export to CSV"
