from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('job_assigned', 'Job Assigned'),
        ('job_completed', 'Job Completed'),
        ('job_application', 'Job Application'),
        ('message_received', 'Message Received'),
        ('payment_received', 'Payment Received'),
        ('review_received', 'Review Received'),
        ('document_verified', 'Document Verified'),
        ('account_update', 'Account Update'),
        ('system_alert', 'System Alert'),
        ('promotion', 'Promotion'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Push notification tracking
    is_pushed = models.BooleanField(default=False)
    pushed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data (JSON for flexibility)
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wc_notification_preferences')
    
    # Email preferences
    email_job_assignments = models.BooleanField(default=True)
    email_job_applications = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    email_reviews = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=False)
    
    # Push notification preferences
    push_job_assignments = models.BooleanField(default=True)
    push_job_applications = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=True)
    push_reviews = models.BooleanField(default=True)
    push_promotions = models.BooleanField(default=False)
    
    # In-app notification preferences
    app_job_assignments = models.BooleanField(default=True)
    app_job_applications = models.BooleanField(default=True)
    app_messages = models.BooleanField(default=True)
    app_payments = models.BooleanField(default=True)
    app_reviews = models.BooleanField(default=True)
    app_promotions = models.BooleanField(default=True)
    
    # General settings
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (no push notifications)")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


class PushToken(models.Model):
    DEVICE_TYPES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    token = models.TextField(unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES)
    device_id = models.CharField(max_length=100, blank=True)
    app_version = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'token']
        
    def __str__(self):
        return f"{self.user.email} - {self.device_type} token"