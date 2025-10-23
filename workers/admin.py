from django.contrib import admin
from .models import (Category, Skill, WorkerProfile, WorkerDocument, WorkExperience,
                     CustomSkillRequest, WorkerCustomSkill, WorkerCustomCategory)


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
