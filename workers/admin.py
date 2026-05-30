from django.contrib import admin
from .models import (Category, Skill, WorkerProfile, WorkerDocument, WorkExperience,
                     CustomSkillRequest, WorkerCustomSkill, WorkerCustomCategory,
                     SavedCard, BankAccount, MobileMoneyAccount)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(CustomSkillRequest)
class CustomSkillRequestAdmin(admin.ModelAdmin):
    list_display = ['worker', 'request_type', 'name', 'category', 'status', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['worker__user__username', 'name']
    readonly_fields = ['worker', 'request_type', 'name', 'category', 'created_at']
    fieldsets = (
        ('Request Details', {
            'fields': ('worker', 'request_type', 'name', 'category', 'created_at')
        }),
        ('Review', {
            'fields': ('status', 'admin_notes', 'reviewed_at')
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        from datetime import datetime
        for req in queryset.filter(status='pending'):
            if req.request_type == 'category':
                # Create the category
                Category.objects.get_or_create(name=req.name, defaults={'is_active': True})
            elif req.request_type == 'skill' and req.category:
                # Create the skill
                Skill.objects.get_or_create(category=req.category, name=req.name)
            
            req.status = 'approved'
            req.reviewed_at = datetime.now()
            req.save()
        self.message_user(request, f"{queryset.count()} request(s) approved and created.")
    approve_requests.short_description = "Approve selected requests"
    
    def reject_requests(self, request, queryset):
        from datetime import datetime
        queryset.update(status='rejected', reviewed_at=datetime.now())
        self.message_user(request, f"{queryset.count()} request(s) rejected.")
    reject_requests.short_description = "Reject selected requests"


class WorkerDocumentInline(admin.TabularInline):
    model = WorkerDocument
    extra = 0


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'availability', 'verification_status', 'average_rating', 'completed_jobs']
    list_filter = ['availability', 'verification_status', 'is_featured', 'city']
    search_fields = ['user__username', 'user__email', 'city']
    filter_horizontal = ['categories', 'skills']
    inlines = [WorkerDocumentInline, WorkExperienceInline]
    actions = ['bulk_verify_workers', 'bulk_reject_workers', 'bulk_mark_available', 'bulk_mark_unavailable', 
               'bulk_feature_workers', 'bulk_unfeature_workers', 'bulk_send_notification']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Profile', {
            'fields': ('bio', 'categories', 'skills', 'experience_years', 'hourly_rate')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Status', {
            'fields': ('availability', 'verification_status', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('total_jobs', 'completed_jobs', 'average_rating', 'total_earnings')
        }),
    )
    
    # Bulk actions for Worker Profiles
    def bulk_verify_workers(self, request, queryset):
        """Bulk verify worker profiles"""
        count = queryset.filter(verification_status__in=['pending', 'rejected']).update(verification_status='verified')
        
        # Send notifications
        from worker_connect.notification_helpers import notify_system_alert
        for worker in queryset.filter(verification_status='verified'):
            notify_system_alert(
                worker.user,
                'Profile Verified',
                'Congratulations! Your worker profile has been verified. You can now receive job assignments.'
            )
        
        self.message_user(request, f"{count} worker profile(s) verified.")
    bulk_verify_workers.short_description = "✅ Verify Workers"
    
    def bulk_reject_workers(self, request, queryset):
        """Bulk reject worker profiles"""
        count = queryset.filter(verification_status='pending').update(verification_status='rejected')
        
        # Send notifications
        from worker_connect.notification_helpers import notify_system_alert
        for worker in queryset.filter(verification_status='rejected'):
            notify_system_alert(
                worker.user,
                'Profile Verification',
                'Your worker profile verification requires additional review. Please check your documents.'
            )
        
        self.message_user(request, f"{count} worker profile(s) rejected.")
    bulk_reject_workers.short_description = "❌ Reject Workers"
    
    def bulk_mark_available(self, request, queryset):
        """Bulk mark workers as available"""
        count = queryset.update(availability='available')
        self.message_user(request, f"{count} worker(s) marked as available.")
    bulk_mark_available.short_description = "🟢 Mark Available"
    
    def bulk_mark_unavailable(self, request, queryset):
        """Bulk mark workers as unavailable"""
        count = queryset.update(availability='unavailable')
        self.message_user(request, f"{count} worker(s) marked as unavailable.")
    bulk_mark_unavailable.short_description = "🔴 Mark Unavailable"
    
    def bulk_feature_workers(self, request, queryset):
        """Bulk feature workers"""
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} worker(s) featured.")
    bulk_feature_workers.short_description = "⭐ Feature Workers"
    
    def bulk_unfeature_workers(self, request, queryset):
        """Bulk unfeature workers"""
        count = queryset.update(is_featured=False)
        self.message_user(request, f"{count} worker(s) unfeatured.")
    bulk_unfeature_workers.short_description = "⚫ Remove Featured"
    
    def bulk_send_notification(self, request, queryset):
        """Send bulk notification to workers"""
        from worker_connect.notification_helpers import notify_system_alert
        count = 0
        for worker in queryset:
            notify_system_alert(
                worker.user,
                'System Announcement',
                'This is a notification from Worker Connect admin.'
            )
            count += 1
        self.message_user(request, f"Sent notification to {count} worker(s).")
    bulk_send_notification.short_description = "📢 Send Notification"


@admin.register(WorkerDocument)
class WorkerDocumentAdmin(admin.ModelAdmin):
    list_display = ['worker', 'document_type', 'title', 'verification_status', 'uploaded_at']
    list_filter = ['document_type', 'verification_status', 'uploaded_at']
    search_fields = ['worker__user__username', 'title']
    readonly_fields = ['uploaded_at']


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ['worker', 'job_title', 'company', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current', 'start_date']
    search_fields = ['worker__user__username', 'job_title', 'company']


@admin.register(WorkerCustomSkill)
class WorkerCustomSkillAdmin(admin.ModelAdmin):
    list_display = ['worker', 'name', 'years_of_experience', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['worker__user__username', 'name']
    readonly_fields = ['created_at']
    actions = ['verify_skills']
    
    def verify_skills(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} skill(s) verified.")
    verify_skills.short_description = "Mark as verified"


@admin.register(WorkerCustomCategory)
class WorkerCustomCategoryAdmin(admin.ModelAdmin):
    list_display = ['worker', 'name', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['worker__user__username', 'name']
    readonly_fields = ['created_at']
    actions = ['verify_categories']
    
    def verify_categories(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} category(ies) verified.")
    verify_categories.short_description = "Mark as verified"


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_type', 'last_four', 'expiry_month', 'expiry_year', 'is_default', 'is_active', 'created_at']
    list_filter = ['card_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'cardholder_name', 'last_four']
    readonly_fields = ['created_at', 'updated_at', 'stripe_card_id', 'stripe_customer_id']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Card Details', {
            'fields': ('card_type', 'last_four', 'expiry_month', 'expiry_year', 'cardholder_name')
        }),
        ('Stripe', {
            'fields': ('stripe_card_id', 'stripe_customer_id')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'bank_name', 'account_holder_name', 'account_type', 'is_verified', 'is_default', 'is_active', 'created_at']
    list_filter = ['account_type', 'is_verified', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'bank_name', 'account_holder_name']
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_holder_name', 'account_number', 'routing_number', 'swift_code', 'account_type')
        }),
        ('Stripe', {
            'fields': ('stripe_bank_account_id',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['verify_accounts']
    
    def verify_accounts(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} bank account(s) verified.")
    verify_accounts.short_description = "Verify selected accounts"


@admin.register(MobileMoneyAccount)
class MobileMoneyAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'phone_number', 'account_name', 'is_verified', 'is_default', 'is_active', 'created_at']
    list_filter = ['provider', 'is_verified', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number', 'account_name']
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Account Details', {
            'fields': ('provider', 'phone_number', 'account_name')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['verify_accounts']
    
    def verify_accounts(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} mobile money account(s) verified.")
    verify_accounts.short_description = "Verify selected accounts"
