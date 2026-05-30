from django.contrib import admin
from .models import AgentProfile


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'business_name', 'agent_code', 'commission_rate', 'is_verified', 'total_workers', 'created_at']
    list_filter = ['is_verified']
    search_fields = ['user__username', 'user__email', 'business_name', 'agent_code']
    readonly_fields = ['agent_code', 'total_commission_earned', 'created_at', 'updated_at']
    actions = ['approve_agents']

    def approve_agents(self, request, queryset):
        for agent in queryset:
            agent.approve()
        self.message_user(request, f"{queryset.count()} agent(s) approved.")
    approve_agents.short_description = "Approve selected agents"
