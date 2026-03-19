from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import random
import string
from accounts.models import User


class AgentProfile(models.Model):
    """Profile for agents who recruit and manage workers"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    business_name = models.CharField(max_length=200, blank=True, help_text="Business or trading name")
    bio = models.TextField(blank=True, help_text="Short description about the agent")
    agent_code = models.CharField(
        max_length=10, unique=True, blank=True, null=True,
        help_text="Unique code workers use to register under this agent (generated on approval)"
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission percentage earned per job completed by managed workers"
    )
    is_verified = models.BooleanField(default=False, help_text="Set by admin after reviewing the application")
    total_commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_verified']),
            models.Index(fields=['agent_code']),
        ]

    def __str__(self):
        name = self.business_name or self.user.get_full_name() or self.user.username
        status = "✓" if self.is_verified else "pending"
        return f"{name} ({status})"

    @staticmethod
    def generate_unique_code():
        """Generate a unique 6-character alphanumeric agent code."""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not AgentProfile.objects.filter(agent_code=code).exists():
                return code

    def approve(self):
        """Approve the agent and assign a unique code if not already set."""
        if not self.agent_code:
            self.agent_code = self.generate_unique_code()
        self.is_verified = True
        self.save()

    @property
    def total_workers(self):
        return self.workers.count()

    @property
    def display_name(self):
        return self.business_name or self.user.get_full_name() or self.user.username
