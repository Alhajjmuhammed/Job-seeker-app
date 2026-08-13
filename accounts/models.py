from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import RegexValidator, EmailValidator


class UserManager(DjangoUserManager):
    """
    Default createsuperuser doesn't set user_type (it's not in
    REQUIRED_FIELDS, and create_superuser() doesn't call full_clean()), so a
    freshly-created superuser ends up with user_type='' instead of 'admin' -
    is_admin_user/is_staff-based checks still work, but anything filtering
    or displaying by user_type='admin' specifically would silently miss
    them. Default it to 'admin' here so day-one deployment superusers are
    correctly typed without relying on every admin-detection code path
    remembering to also check is_staff.
    """
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('user_type', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with role-based access"""

    objects = UserManager()
    
    USER_TYPE_CHOICES = (
        ('worker', 'Worker'),
        ('client', 'Client'),
        ('admin', 'Admin'),
        ('agent', 'Agent'),
    )
    
    # Make email required and unique
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        error_messages={
            'unique': 'A user with this email already exists.',
        }
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Profile visibility preferences
    show_email = models.BooleanField(default=False, help_text="Show email on public profile")
    show_phone = models.BooleanField(default=False, help_text="Show phone number on public profile")
    allow_search_indexing = models.BooleanField(default=True, help_text="Allow profile to appear in search results")

    # GDPR consent flags (Article 6/7) - explicit opt-in for non-essential
    # data uses. essential_cookies/data_processing are not stored here since
    # they're required for the service to function and aren't withdrawable
    # without account deletion (see accounts/gdpr_views.py::consent_status).
    consent_analytics = models.BooleanField(default=False, help_text="Consent to usage analytics tracking")
    consent_personalization = models.BooleanField(default=False, help_text="Consent to personalized recommendations")
    consent_third_party_sharing = models.BooleanField(default=False, help_text="Consent to sharing data with third-party partners")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use email as username field for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_worker(self):
        return self.user_type == 'worker'
    
    @property
    def is_client(self):
        return self.user_type == 'client'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin' or self.is_staff

    @property
    def is_agent(self):
        return self.user_type == 'agent'


# NotificationPreferences is defined in notification_preferences.py, not
# here - Django only auto-discovers models actually imported into an app's
# models.py, so without this import the model is invisible to the app
# registry (no reverse relation on User, no cascade-delete on user removal)
# even though its table and migrations are real. This import is the fix.
from .notification_preferences import NotificationPreferences  # noqa: E402,F401
