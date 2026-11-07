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


# ---- job posts (vacancies) - read-mostly views for support staff
from .vacancy_models import EmploymentContract, Vacancy, VacancyApplication  # noqa: E402


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'poster', 'kind', 'category', 'city', 'workers_needed', 'status', 'closing_date')
    list_filter = ('status', 'kind', 'duration', 'category')
    search_fields = ('title', 'company_name', 'city', 'poster__email')
    raw_id_fields = ('poster', 'reviewed_by')


@admin.register(VacancyApplication)
class VacancyApplicationAdmin(admin.ModelAdmin):
    list_display = ('vacancy', 'worker', 'status', 'created_at')
    list_filter = ('status',)
    raw_id_fields = ('vacancy', 'worker', 'decided_by')


@admin.register(EmploymentContract)
class EmploymentContractAdmin(admin.ModelAdmin):
    list_display = ('vacancy', 'worker', 'employer', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
    raw_id_fields = ('application', 'vacancy', 'worker', 'employer', 'ended_by', 'renewed_from')
