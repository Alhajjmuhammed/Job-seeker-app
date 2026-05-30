"""
Payment models for Worker Connect.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


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
        'workers.WorkerProfile',
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
        'workers.WorkerProfile',
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
            SavedCard.objects.filter(user=self.user, is_default=True).update(is_default=False)
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
        return f"{self.bank_name} - ****{self.account_number[-4:]}"
    
    def save(self, *args, **kwargs):
        # If this account is set as default, unset other defaults for this user
        if self.is_default:
            BankAccount.objects.filter(user=self.user, is_default=True).update(is_default=False)
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
            MobileMoneyAccount.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)