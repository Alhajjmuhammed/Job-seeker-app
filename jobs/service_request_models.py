"""
Service Request Models for Admin-Mediated Workflow
Admin assigns workers to client service requests
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from accounts.models import User
from workers.models import WorkerProfile, Category


class ServiceRequest(models.Model):
    """
    Client service requests - Admin assigns workers to these
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending Assignment'),
        ('assigned', 'Worker Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    URGENCY_CHOICES = (
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    )
    
    DURATION_TYPE_CHOICES = (
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('3_months', '3 Months'),
        ('6_months', '6 Months'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Date Range'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    )
    
    # Request info
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_requests')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='service_requests')
    
    title = models.CharField(max_length=200, help_text="Brief description of service needed")
    description = models.TextField(help_text="Detailed description of work required")
    
    # Location
    location = models.CharField(max_length=255, help_text="Service location address")
    city = models.CharField(max_length=100)
    
    # Scheduling
    preferred_date = models.DateField(null=True, blank=True, help_text="Preferred date for service")
    preferred_time = models.TimeField(null=True, blank=True, help_text="Preferred time for service")
    
    # Duration & Pricing (NEW SYSTEM)
    duration_type = models.CharField(
        max_length=20,
        choices=DURATION_TYPE_CHOICES,
        default='daily',
        help_text="Service duration type"
    )
    duration_days = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Total number of days for service"
    )
    service_start_date = models.DateField(null=True, blank=True, help_text="Service start date (for custom range)")
    service_end_date = models.DateField(null=True, blank=True, help_text="Service end date (for custom range)")
    
    # Pricing
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Daily rate at time of booking"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total price (daily_rate × duration_days)"
    )
    
    # Payment
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Payment status"
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method used (fake for demo)"
    )
    paid_at = models.DateTimeField(null=True, blank=True, help_text="When payment was completed")
    payment_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Payment transaction ID (fake for demo)"
    )
    
    # Legacy field (keep for backward compatibility)
    estimated_duration_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5)],
        help_text="DEPRECATED: Use duration_days instead"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal')
    
    # Assignment (by admin)
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_requests'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_assignments_made',
        help_text="Admin who assigned the worker"
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Worker response
    worker_accepted = models.BooleanField(null=True, blank=True, help_text="Worker acceptance status")
    worker_response_at = models.DateTimeField(null=True, blank=True)
    worker_rejection_reason = models.TextField(blank=True)
    
    # Completion
    work_started_at = models.DateTimeField(null=True, blank=True)
    work_completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_worker_at = models.DateTimeField(null=True, blank=True, help_text="When worker confirmed completion")
    
    # Billing
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Hourly rate for this service"
    )
    total_hours_worked = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Actual hours worked (from time tracking)"
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Total amount (hours × rate)"
    )
    
    # Notes
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")
    client_notes = models.TextField(blank=True, help_text="Additional notes from client")
    completion_notes = models.TextField(blank=True, help_text="Worker's completion notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['assigned_worker', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['urgency', 'status']),
        ]
    
    def __str__(self):
        return f"Service Request #{self.id} - {self.title} ({self.get_status_display()})"
    
    def calculate_duration_days(self):
        """Calculate duration in days based on duration type"""
        duration_map = {
            'daily': 1,
            'monthly': 30,
            '3_months': 90,
            '6_months': 180,
            'yearly': 365,
        }
        
        if self.duration_type == 'custom':
            if self.service_start_date and self.service_end_date:
                delta = self.service_end_date - self.service_start_date
                return max(1, delta.days + 1)  # +1 to include both start and end days
            return 1
        
        return duration_map.get(self.duration_type, 1)
    
    def calculate_total_price(self):
        """Calculate total price based on daily rate and duration"""
        if self.duration_type == 'custom':
            self.duration_days = self.calculate_duration_days()
        else:
            self.duration_days = self.calculate_duration_days()
        
        if self.daily_rate and self.duration_days:
            self.total_price = self.daily_rate * Decimal(str(self.duration_days))
            return self.total_price
        return Decimal('0.00')
    
    def calculate_total_amount(self):
        """Calculate total based on hours worked and hourly rate (legacy)"""
        if self.hourly_rate and self.total_hours_worked:
            self.total_amount = self.hourly_rate * self.total_hours_worked
            return self.total_amount
        return Decimal('0.00')
    
    def assign_worker(self, worker, admin_user, notes=''):
        """Admin assigns a worker to this service request"""
        self.assigned_worker = worker
        self.assigned_by = admin_user
        self.assigned_at = timezone.now()
        self.status = 'assigned'
        if notes:
            self.admin_notes = notes
        self.save()
        
        # Create notification for worker
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_assigned(self, worker)
        
        return True
    
    def worker_accept(self):
        """Worker accepts the assignment"""
        self.worker_accepted = True
        self.worker_response_at = timezone.now()
        self.status = 'in_progress'
        self.save()
        
        # Notify client
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_accepted(self)
        
        return True
    
    def worker_reject(self, reason=''):
        """Worker rejects the assignment"""
        self.worker_accepted = False
        self.worker_response_at = timezone.now()
        self.worker_rejection_reason = reason
        self.status = 'pending'  # Back to pending for admin to reassign
        self.assigned_worker = None  # Clear assignment
        self.save()
        
        # Notify admin
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_rejected(self, reason)
        
        return True
    
    def mark_completed_by_worker(self, completion_notes=''):
        """Worker confirms work is done"""
        self.completed_by_worker_at = timezone.now()
        self.work_completed_at = timezone.now()
        self.status = 'completed'
        self.completion_notes = completion_notes
        
        # Calculate final billing
        self.calculate_total_amount()
        self.save()
        
        # Update worker stats
        if self.assigned_worker:
            self.assigned_worker.completed_jobs += 1
            self.assigned_worker.save()
        
        # Notify client
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_completed(self)
        
        return True


class TimeTracking(models.Model):
    """
    Track worker clock in/out times for service requests
    """
    
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='time_logs'
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='time_logs'
    )
    
    # Time tracking
    clock_in = models.DateTimeField(help_text="When worker started work")
    clock_out = models.DateTimeField(null=True, blank=True, help_text="When worker finished work")
    
    # Location tracking (optional)
    clock_in_location = models.CharField(max_length=255, blank=True)
    clock_out_location = models.CharField(max_length=255, blank=True)
    
    # Calculated duration
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated duration in hours"
    )
    
    # Notes
    notes = models.TextField(blank=True, help_text="Work notes, issues encountered, etc.")
    
    # Verification
    verified_by_client = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-clock_in']
        indexes = [
            models.Index(fields=['service_request', '-clock_in']),
            models.Index(fields=['worker', '-clock_in']),
        ]
    
    def __str__(self):
        return f"Time Log - {self.worker.user.username} - {self.clock_in.strftime('%Y-%m-%d %H:%M')}"
    
    def calculate_duration(self):
        """Calculate duration between clock in and clock out"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            self.duration_hours = Decimal(str(round(duration.total_seconds() / 3600, 2)))
            return self.duration_hours
        return None
    
    def clock_out_now(self, notes='', location=''):
        """Clock out worker"""
        self.clock_out = timezone.now()
        if notes:
            self.notes = notes
        if location:
            self.clock_out_location = location
        
        # Calculate duration
        self.calculate_duration()
        self.save()
        
        # Update service request total hours
        self.update_service_request_hours()
        
        return True
    
    def update_service_request_hours(self):
        """Update total hours in service request"""
        if self.duration_hours:
            # Sum all time logs for this service request
            from django.db.models import Sum
            total = TimeTracking.objects.filter(
                service_request=self.service_request,
                clock_out__isnull=False
            ).aggregate(total=Sum('duration_hours'))['total'] or Decimal('0.00')
            
            self.service_request.total_hours_worked = total
            self.service_request.calculate_total_amount()
            self.service_request.save()


class WorkerActivity(models.Model):
    """
    Log of all worker activities for history tracking
    """
    
    ACTIVITY_TYPE_CHOICES = (
        ('assigned', 'Assigned to Service'),
        ('accepted', 'Accepted Assignment'),
        ('rejected', 'Rejected Assignment'),
        ('started', 'Started Work'),
        ('paused', 'Paused Work'),
        ('resumed', 'Resumed Work'),
        ('completed', 'Completed Work'),
        ('cancelled', 'Service Cancelled'),
    )
    
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='activity_log'
    )
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='activity_log',
        null=True,
        blank=True
    )
    
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField(help_text="Activity description")
    
    # Metadata
    location = models.CharField(max_length=255, blank=True)
    duration = models.DurationField(null=True, blank=True)
    amount_earned = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['worker', '-created_at']),
            models.Index(fields=['service_request', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
        verbose_name_plural = 'Worker Activities'
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.get_activity_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @staticmethod
    def log_activity(worker, activity_type, description, service_request=None, **kwargs):
        """Helper method to log worker activity"""
        activity = WorkerActivity.objects.create(
            worker=worker,
            service_request=service_request,
            activity_type=activity_type,
            description=description,
            location=kwargs.get('location', ''),
            duration=kwargs.get('duration', None),
            amount_earned=kwargs.get('amount_earned', None)
        )
        return activity
