from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from accounts.models import User


class Category(models.Model):
    """Job categories for workers"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    is_active = models.BooleanField(default=True)
    daily_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=25.00,
        validators=[MinValueValidator(0)],
        help_text="Daily rate in USD for this service category"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Skill(models.Model):
    """Skills related to categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['name']
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class WorkerProfile(models.Model):
    """Extended profile for workers"""
    
    WORKER_TYPE_CHOICES = (
        ('professional', 'Professional'),
        ('non_academic', 'Non-Academic'),
    )
    
    AVAILABILITY_CHOICES = (
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    worker_type = models.CharField(max_length=20, choices=WORKER_TYPE_CHOICES, default='non_academic')
    bio = models.TextField(blank=True, help_text="Brief introduction about yourself")
    profile_image = models.FileField(upload_to='worker_profiles/', blank=True, null=True, help_text="Profile photo")
    
    # Profile completion tracking
    profile_completion_percentage = models.IntegerField(default=0)
    is_profile_complete = models.BooleanField(default=False)
    has_uploaded_national_id = models.BooleanField(default=False)
    
    # Location
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Tanzania')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Personal details
    RELIGION_CHOICES = (
        ('', 'Prefer not to say'),
        ('islam', 'Islam'),
        ('christianity', 'Christianity'),
        ('judaism', 'Judaism'),
        ('hinduism', 'Hinduism'),
        ('buddhism', 'Buddhism'),
        ('sikhism', 'Sikhism'),
        ('other', 'Other'),
    )
    
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, blank=True, default='')
    can_work_everywhere = models.BooleanField(default=False, help_text="Available to work in any location")
    
    # Work details
    categories = models.ManyToManyField(Category, related_name='workers')
    skills = models.ManyToManyField(Skill, related_name='workers', blank=True)
    experience_years = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(70)])
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Status
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    is_featured = models.BooleanField(default=False)
    
    # Statistics
    total_jobs = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    completed_jobs = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    # Agent relationship - worker may be recruited by an agent
    agent = models.ForeignKey(
        'agents.AgentProfile',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='workers',
        help_text="Agent who recruited this worker (optional)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['availability']),
            models.Index(fields=['city']),
            models.Index(fields=['worker_type']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['-created_at']),
            # Composite indexes for common query patterns
            models.Index(fields=['verification_status', 'availability', '-average_rating']),
            models.Index(fields=['city', 'verification_status']),
            models.Index(fields=['verification_status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Worker Profile"
    
    @property
    def has_id_document(self):
        """Check if worker has uploaded ID document (required for verification)"""
        return self.documents.filter(document_type='id').exists()
    
    @property
    def can_accept_direct_hires(self):
        """Worker can accept direct hire requests if they have ID and are verified"""
        return self.has_id_document and self.verification_status == 'verified'
    
    @property
    def completion_rate(self):
        if self.total_jobs > 0:
            return round((self.completed_jobs / self.total_jobs) * 100, 2)
        return 0
    
    @property
    def profile_completion(self):
        """Calculate profile completion percentage"""
        total_fields = 0
        completed_fields = 0
        
        # Check basic profile fields
        fields_to_check = [
            self.bio,
            self.address,
            self.city,
            self.state,
            self.country,
            self.postal_code,
        ]
        
        for field in fields_to_check:
            total_fields += 1
            if field and str(field).strip():
                completed_fields += 1
        
        # Check profile image
        total_fields += 1
        if self.profile_image:
            completed_fields += 1
        
        # Check categories (at least one)
        total_fields += 1
        if self.categories.exists():
            completed_fields += 1
        
        # Check experience years
        total_fields += 1
        if self.experience_years > 0:
            completed_fields += 1
        
        # Check hourly rate
        total_fields += 1
        if self.hourly_rate:
            completed_fields += 1
        
        # Check if has at least one document
        total_fields += 1
        if self.documents.exists():
            completed_fields += 1
        
        # Check if has at least one experience
        total_fields += 1
        if self.experiences.exists():
            completed_fields += 1
        
        # Check if has at least one custom skill
        total_fields += 1
        if self.custom_skills.exists():
            completed_fields += 1
        
        # Calculate percentage
        if total_fields > 0:
            return round((completed_fields / total_fields) * 100)
        return 0


class WorkerDocument(models.Model):
    """Documents uploaded by workers - Only ID required for basic verification"""
    
    DOCUMENT_TYPES = (
        ('id', 'ID Card (Required)'),  # Only this is mandatory
        ('cv', 'CV/Resume (Optional)'),
        ('certificate', 'Certificate (Optional)'),
        ('license', 'License (Optional)'),
        ('other', 'Other (Optional)'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='worker_documents/')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_required = models.BooleanField(default=False, help_text="Is this document required for verification?")
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        # Mark ID as required
        if self.document_type == 'id':
            self.is_required = True
        super().save(*args, **kwargs)
    
    @property
    def is_id_document(self):
        """Check if this is an ID document"""
        return self.document_type == 'id'


class WorkExperience(models.Model):
    """Work experience for workers"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='experiences')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.job_title} at {self.company}"
    
    @property
    def duration(self):
        """Calculate the duration of work experience"""
        from datetime import date
        
        end = self.end_date if self.end_date else date.today()
        
        # Calculate total months
        months_diff = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        
        years = months_diff // 12
        months = months_diff % 12
        
        if years > 0 and months > 0:
            return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''}"
        elif years > 0:
            return f"{years} year{'s' if years > 1 else ''}"
        elif months > 0:
            return f"{months} month{'s' if months > 1 else ''}"
        else:
            return "Less than a month"


class CustomSkillRequest(models.Model):
    """Workers can request custom skills/categories not in the system"""
    
    REQUEST_TYPES = (
        ('category', 'Category'),
        ('skill', 'Skill'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    name = models.CharField(max_length=200, help_text="Name of the requested category or skill")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, 
                                 help_text="For skill requests, which category does it belong to?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin feedback")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'request_type', 'name', 'category']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.get_request_type_display()}: {self.name}"


class WorkerCustomSkill(models.Model):
    """Custom skills added by workers with optional certificates"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_skills')
    name = models.CharField(max_length=200, help_text="Skill name")
    description = models.TextField(blank=True, help_text="Brief description of this skill")
    certificate = models.FileField(upload_to='skill_certificates/', null=True, blank=True, 
                                   help_text="Upload certificate (optional)")
    years_of_experience = models.IntegerField(default=0, help_text="Years of experience with this skill")
    is_verified = models.BooleanField(default=False, help_text="Admin verified this skill")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'name']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.name}"


class WorkerCustomCategory(models.Model):
    """Custom categories added by workers"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_categories')
    name = models.CharField(max_length=200, help_text="Category name")
    description = models.TextField(blank=True, help_text="What services do you offer in this category?")
    is_verified = models.BooleanField(default=False, help_text="Admin verified this category")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'name']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.name}"


class Payment(models.Model):
    """Payment model for job transactions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('held', 'Held in Escrow'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TYPE_CHOICES = [
        ('job_payment', 'Job Payment'),
        ('deposit', 'Deposit'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
        ('fee', 'Platform Fee'),
    ]
    
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number = models.CharField(max_length=50, unique=True)
    
    # Parties
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='payments_made',
        null=True, blank=True
    )
    worker = models.ForeignKey(
        'WorkerProfile',
        on_delete=models.CASCADE,
        related_name='payments_received',
        null=True, blank=True
    )
    
    # Job reference
    job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True, blank=True
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    worker_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='job_payment')
    
    # External payment provider data
    external_payment_id = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=50, default='stripe')
    provider_data = models.JSONField(default=dict, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_number} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        # Calculate platform fee and worker amount
        if not self.platform_fee:
            self.platform_fee = self.calculate_platform_fee()
        
        if not self.worker_amount:
            self.worker_amount = self.amount - self.platform_fee
        
        super().save(*args, **kwargs)
    
    def generate_payment_number(self) -> str:
        """Generate unique payment number"""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_part = str(uuid.uuid4())[:8].upper()
        return f"PAY-{timestamp}-{random_part}"
    
    def calculate_platform_fee(self) -> Decimal:
        """Calculate platform fee (e.g., 10% of amount)"""
        from django.conf import settings
        fee_percentage = getattr(settings, 'PLATFORM_FEE_PERCENTAGE', Decimal('10.0'))
        return self.amount * (fee_percentage / 100)


class WorkerEarning(models.Model):
    """Track worker earnings from completed jobs"""
    
    worker = models.ForeignKey(
        'WorkerProfile',
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    
    job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-earned_at']
        unique_together = ['worker', 'job', 'payment']
    
    def __str__(self):
        return f"{self.worker} earned ${self.amount} from {self.job}"


class SavedCard(models.Model):
    """Saved credit/debit card for payments"""
    
    CARD_TYPE_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Other'),
    ]
    
    # Owner
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_cards'
    )
    
    # Card details (tokenized - never store actual card number)
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES)
    last_four = models.CharField(max_length=4)
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    cardholder_name = models.CharField(max_length=255)
    
    # External provider data
    stripe_card_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255)
    
    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.card_type.upper()} ****{self.last_four}"
    
    def save(self, *args, **kwargs):
        # If this card is set as default, unset other defaults for this user
        if self.is_default:
            SavedCard.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class BankAccount(models.Model):
    """Bank account for worker payouts"""
    
    # Owner (workers only)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    
    # Bank details
    bank_name = models.CharField(max_length=255)
    account_holder_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Account type
    account_type = models.CharField(
        max_length=20,
        choices=[('checking', 'Checking'), ('savings', 'Savings')],
        default='checking'
    )
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # External provider data
    stripe_bank_account_id = models.CharField(max_length=255, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        if len(self.account_number) > 4:
            return f"{self.bank_name} - ****{self.account_number[-4:]}"
        return f"{self.bank_name} - {self.account_number}"
    
    def save(self, *args, **kwargs):
        # If this account is set as default, unset other defaults for this user
        if self.is_default:
            BankAccount.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class MobileMoneyAccount(models.Model):
    """Mobile money account for worker payouts (M-Pesa, Tigo Pesa, etc.)"""
    
    PROVIDER_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('tigo_pesa', 'Tigo Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('halopesa', 'Halopesa'),
        ('other', 'Other'),
    ]
    
    # Owner (workers only)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mobile_money_accounts'
    )
    
    # Account details
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    phone_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.get_provider_display()} - {self.phone_number}"
    
    def save(self, *args, **kwargs):
        # If this account is set as default, unset other defaults for this user
        if self.is_default:
            MobileMoneyAccount.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
