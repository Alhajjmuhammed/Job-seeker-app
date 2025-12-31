"""
Notification preferences for Worker Connect.

Allows users to manage their notification settings.
"""

from django.db import models
from typing import Dict, Any


class NotificationPreferences(models.Model):
    """
    User notification preferences.
    """
    
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_new_jobs = models.BooleanField(default=True)
    email_job_applications = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_job_updates = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    email_weekly_digest = models.BooleanField(default=True)
    
    # Push notifications
    push_new_jobs = models.BooleanField(default=True)
    push_job_applications = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_job_updates = models.BooleanField(default=True)
    push_reminders = models.BooleanField(default=True)
    
    # SMS notifications (premium)
    sms_job_applications = models.BooleanField(default=False)
    sms_urgent_messages = models.BooleanField(default=False)
    
    # Frequency settings
    FREQUENCY_CHOICES = [
        ('instant', 'Instant'),
        ('hourly', 'Hourly Digest'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
    ]
    email_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='instant'
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Notification preferences'
    
    def __str__(self):
        return f"Notification preferences for {self.user}"


class NotificationPreferencesService:
    """
    Service for managing notification preferences.
    """
    
    @staticmethod
    def get_or_create_preferences(user) -> 'NotificationPreferences':
        """
        Get or create notification preferences for a user.
        """
        prefs, _ = NotificationPreferences.objects.get_or_create(user=user)
        return prefs
    
    @staticmethod
    def get_preferences_dict(user) -> Dict[str, Any]:
        """
        Get preferences as a dictionary.
        """
        prefs = NotificationPreferencesService.get_or_create_preferences(user)
        
        return {
            'email': {
                'new_jobs': prefs.email_new_jobs,
                'job_applications': prefs.email_job_applications,
                'messages': prefs.email_messages,
                'job_updates': prefs.email_job_updates,
                'marketing': prefs.email_marketing,
                'weekly_digest': prefs.email_weekly_digest,
                'frequency': prefs.email_frequency,
            },
            'push': {
                'new_jobs': prefs.push_new_jobs,
                'job_applications': prefs.push_job_applications,
                'messages': prefs.push_messages,
                'job_updates': prefs.push_job_updates,
                'reminders': prefs.push_reminders,
            },
            'sms': {
                'job_applications': prefs.sms_job_applications,
                'urgent_messages': prefs.sms_urgent_messages,
            },
            'quiet_hours': {
                'enabled': prefs.quiet_hours_enabled,
                'start': prefs.quiet_hours_start.strftime('%H:%M') if prefs.quiet_hours_start else None,
                'end': prefs.quiet_hours_end.strftime('%H:%M') if prefs.quiet_hours_end else None,
            },
        }
    
    @staticmethod
    def update_preferences(
        user,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update notification preferences.
        
        Args:
            user: User instance
            updates: Dict with category -> setting -> value
            
        Example:
            {
                'email': {'new_jobs': False, 'frequency': 'daily'},
                'push': {'messages': True},
            }
        """
        prefs = NotificationPreferencesService.get_or_create_preferences(user)
        
        # Map category/setting to model field
        field_map = {
            'email': {
                'new_jobs': 'email_new_jobs',
                'job_applications': 'email_job_applications',
                'messages': 'email_messages',
                'job_updates': 'email_job_updates',
                'marketing': 'email_marketing',
                'weekly_digest': 'email_weekly_digest',
                'frequency': 'email_frequency',
            },
            'push': {
                'new_jobs': 'push_new_jobs',
                'job_applications': 'push_job_applications',
                'messages': 'push_messages',
                'job_updates': 'push_job_updates',
                'reminders': 'push_reminders',
            },
            'sms': {
                'job_applications': 'sms_job_applications',
                'urgent_messages': 'sms_urgent_messages',
            },
            'quiet_hours': {
                'enabled': 'quiet_hours_enabled',
                'start': 'quiet_hours_start',
                'end': 'quiet_hours_end',
            },
        }
        
        updated_fields = []
        
        for category, settings in updates.items():
            if category not in field_map:
                continue
            
            for setting, value in settings.items():
                if setting not in field_map[category]:
                    continue
                
                field_name = field_map[category][setting]
                
                # Handle time fields
                if field_name in ['quiet_hours_start', 'quiet_hours_end']:
                    from datetime import datetime
                    if value:
                        value = datetime.strptime(value, '%H:%M').time()
                    else:
                        value = None
                
                setattr(prefs, field_name, value)
                updated_fields.append(f"{category}.{setting}")
        
        prefs.save()
        
        return {
            'success': True,
            'updated_fields': updated_fields,
            'preferences': NotificationPreferencesService.get_preferences_dict(user),
        }
    
    @staticmethod
    def should_notify(
        user,
        notification_type: str,
        channel: str = 'push'
    ) -> bool:
        """
        Check if user should receive a notification.
        
        Args:
            user: User instance
            notification_type: Type of notification (new_jobs, messages, etc.)
            channel: Notification channel (email, push, sms)
        """
        from django.utils import timezone
        
        try:
            prefs = NotificationPreferences.objects.get(user=user)
        except NotificationPreferences.DoesNotExist:
            return True  # Default to enabled
        
        # Check quiet hours
        if prefs.quiet_hours_enabled and prefs.quiet_hours_start and prefs.quiet_hours_end:
            now = timezone.localtime().time()
            
            if prefs.quiet_hours_start <= prefs.quiet_hours_end:
                # Normal range (e.g., 22:00 - 06:00 would need special handling)
                in_quiet_hours = prefs.quiet_hours_start <= now <= prefs.quiet_hours_end
            else:
                # Overnight range (e.g., 22:00 - 06:00)
                in_quiet_hours = now >= prefs.quiet_hours_start or now <= prefs.quiet_hours_end
            
            if in_quiet_hours:
                return False
        
        # Check channel-specific setting
        field_name = f"{channel}_{notification_type}"
        if hasattr(prefs, field_name):
            return getattr(prefs, field_name)
        
        return True  # Default to enabled if setting doesn't exist
    
    @staticmethod
    def mute_all(user, channel: str = None) -> Dict[str, Any]:
        """
        Mute all notifications, optionally for a specific channel.
        """
        prefs = NotificationPreferencesService.get_or_create_preferences(user)
        
        if channel == 'email' or channel is None:
            prefs.email_new_jobs = False
            prefs.email_job_applications = False
            prefs.email_messages = False
            prefs.email_job_updates = False
            prefs.email_marketing = False
        
        if channel == 'push' or channel is None:
            prefs.push_new_jobs = False
            prefs.push_job_applications = False
            prefs.push_messages = False
            prefs.push_job_updates = False
            prefs.push_reminders = False
        
        if channel == 'sms' or channel is None:
            prefs.sms_job_applications = False
            prefs.sms_urgent_messages = False
        
        prefs.save()
        
        return {
            'success': True,
            'muted_channel': channel or 'all',
            'message': 'Notifications muted'
        }
    
    @staticmethod
    def unmute_all(user, channel: str = None) -> Dict[str, Any]:
        """
        Unmute all notifications, optionally for a specific channel.
        """
        prefs = NotificationPreferencesService.get_or_create_preferences(user)
        
        if channel == 'email' or channel is None:
            prefs.email_new_jobs = True
            prefs.email_job_applications = True
            prefs.email_messages = True
            prefs.email_job_updates = True
            # Don't enable marketing by default
        
        if channel == 'push' or channel is None:
            prefs.push_new_jobs = True
            prefs.push_job_applications = True
            prefs.push_messages = True
            prefs.push_job_updates = True
            prefs.push_reminders = True
        
        prefs.save()
        
        return {
            'success': True,
            'unmuted_channel': channel or 'all',
            'message': 'Notifications unmuted'
        }
