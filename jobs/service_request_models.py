"""
Service Request Models for Admin-Mediated Workflow
Admin assigns workers to client service requests
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
    latitude = models.FloatField(null=True, blank=True, help_text="GPS latitude of the service location")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS longitude of the service location")

    # Client's requested worker (optional) - admin still confirms before it
    # becomes a real assignment; separate from assigned_worker/assignments
    # below, which always represent an admin's actual decision.
    preferred_worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_by_requests',
        help_text="Worker the client requested; admin confirms or picks someone else"
    )

    ASSIGNMENT_MODE_CHOICES = (
        ('admin_choice', 'Admin Chooses'),
        ('client_choice', 'Client Chose a Worker'),
        ('auto_nearest', 'Auto-Assigned Nearest'),
    )
    assignment_mode = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_MODE_CHOICES,
        default='admin_choice',
        help_text="How the worker for this request is meant to be selected"
    )

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
    
    # Multiple Workers Support
    workers_needed = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Number of workers needed for this service (1-100)"
    )
    
    # Pricing
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Category amount per worker at time of booking"
    )
    service_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Platform service fee at time of booking, charged once per request"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total price ((daily_rate × workers_needed) + service_fee)"
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
    payment_screenshot = models.ImageField(
        upload_to='payment_screenshots/',
        null=True,
        blank=True,
        help_text="Payment proof screenshot uploaded by client"
    )
    payment_verified = models.BooleanField(
        default=False,
        help_text="Admin verified payment screenshot"
    )
    payment_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        help_text="Admin who verified payment"
    )
    payment_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was verified"
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
    
    # Assignment (by admin) - LEGACY: kept for backward compatibility with single worker
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_requests',
        help_text="LEGACY: First assigned worker (use assignments relation for multiple workers)"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_assignments_made',
        help_text="Admin who assigned the worker(s)"
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
    
    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="When request was cancelled")
    cancellation_reason = models.TextField(blank=True, help_text="Reason for cancellation")
    
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
    
    # Ratings
    client_rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Client's rating of worker (1-5 stars)")
    client_review = models.TextField(blank=True, help_text="Client's review of the service")
    
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
    
    @property
    def duration_type_display(self):
        """Get human-readable duration type"""
        return dict(self.DURATION_TYPE_CHOICES).get(self.duration_type, self.duration_type)
    
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
        """Calculate total price based on daily rate, duration, and number of workers"""
        # For fixed duration types (daily/monthly/3_months/6_months/yearly),
        # duration_type is authoritative - always derive duration_days from
        # it rather than trusting whatever duration_days currently holds
        # (which defaults to 1 and previously only got recalculated if it
        # was still unset/zero, silently billing every non-daily request
        # for a single day whenever a caller didn't also set duration_days
        # explicitly). Only 'custom' relies on the start/end date range.
        if self.duration_type == 'custom':
            if self.service_start_date and self.service_end_date:
                self.duration_days = self.calculate_duration_days()
            elif not self.duration_days or self.duration_days == 0:
                self.duration_days = self.calculate_duration_days()
        else:
            self.duration_days = self.calculate_duration_days()
        
        # Pricing is per request, not per day: (amount x workers) + one
        # service fee. duration_days is still derived above so the schedule is
        # recorded accurately, but it no longer affects what the client pays.
        workers_count = self.workers_needed if self.workers_needed else 1
        rate = Decimal(str(self.daily_rate or '0.00'))
        fee = Decimal(str(self.service_fee or '0.00'))
        self.total_price = (rate * Decimal(str(workers_count))) + fee
        return self.total_price

    @staticmethod
    def quote(category, workers_needed=1):
        """
        Price a request without creating one, so the quote a client is shown
        and the record that is stored can never disagree.
        """
        workers = max(1, int(workers_needed or 1))
        rate = Decimal(str(getattr(category, 'daily_rate', None) or '0.00'))
        fee = Decimal(str(getattr(category, 'service_fee', None) or '0.00'))
        return {
            'daily_rate': rate,
            'amount_per_worker': rate,
            'workers_needed': workers,
            'service_fee': fee,
            'total_price': (rate * Decimal(str(workers))) + fee,
        }
    
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

    def cancel(self, reason=''):
        """
        Cancel this request: release every active assignment and free up
        each assigned worker's availability (if they have no other active
        job), then mark the request cancelled and notify the affected
        workers.

        Every call site used to just flip status to 'cancelled' directly,
        leaving ServiceRequestAssignment rows and worker.availability
        untouched - a worker marked 'busy' by an accepted assignment
        stayed busy forever (invisible to admin's available-workers list),
        and could still clock in or mark the job complete after the client
        had already cancelled it.
        """
        from django.db import transaction

        with transaction.atomic():
            locked = ServiceRequest.objects.select_for_update().get(pk=self.pk)
            active_assignments = locked.assignments.filter(
                status__in=['pending', 'accepted', 'in_progress']
            ).select_related('worker')

            for assignment in active_assignments:
                assignment.status = 'cancelled'
                assignment.save(update_fields=['status', 'updated_at'])
                if not assignment._worker_has_other_active_jobs():
                    assignment.worker.availability = 'available'
                    assignment.worker.save(update_fields=['availability'])

            locked.status = 'cancelled'
            locked.cancelled_at = timezone.now()
            if reason:
                locked.cancellation_reason = reason
            locked.save(update_fields=['status', 'cancelled_at', 'cancellation_reason'])

        self.status = locked.status
        self.cancelled_at = locked.cancelled_at
        self.cancellation_reason = locked.cancellation_reason

        from worker_connect.notification_service import NotificationService
        NotificationService.notify_service_cancelled(self)

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


class ServiceRequestAssignment(models.Model):
    """
    Individual worker assignments for service requests
    Supports multiple workers assigned to the same service request
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending Worker Response'),
        ('accepted', 'Accepted by Worker'),
        ('rejected', 'Rejected by Worker'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Links
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="The service request this assignment is for"
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='service_assignments',
        help_text="The worker assigned to this service"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_assignments_created',
        help_text="Admin who made this assignment"
    )
    
    # Assignment info
    assignment_number = models.IntegerField(
        default=1,
        help_text="Worker number (e.g., 1 of 3)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Assignment status"
    )
    
    # Worker response
    worker_accepted = models.BooleanField(
        null=True,
        blank=True,
        help_text="Worker acceptance status"
    )
    worker_response_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When worker responded"
    )
    worker_rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection if rejected"
    )
    
    # Work tracking
    work_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When worker started work"
    )
    work_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When work was completed"
    )
    completion_notes = models.TextField(
        blank=True,
        help_text="Worker's completion notes"
    )
    
    # Billing (per worker)
    worker_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="What this worker earns for the request (the category amount, once)"
    )
    total_hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Total hours this worker spent"
    )
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Admin notes for this specific assignment"
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['service_request', 'assignment_number']
        unique_together = [['service_request', 'worker']]
        indexes = [
            models.Index(fields=['service_request', 'status']),
            models.Index(fields=['worker', 'status']),
            models.Index(fields=['status', '-assigned_at']),
        ]
    
    def __str__(self):
        return f"Assignment #{self.assignment_number} - {self.worker.user.get_full_name()} - SR#{self.service_request.id}"
    
    def accept_assignment(self):
        """Worker accepts this assignment"""
        self.worker_accepted = True
        self.worker_response_at = timezone.now()
        self.status = 'accepted'
        self.save()
        
        # AUTO-UPDATE: Set worker to busy when accepting assignment
        self.worker.availability = 'busy'
        self.worker.save()
        
        # Check if this is the first acceptance - update main request status
        self._update_main_request_status()
        
        # Note: Notifications are handled in the API view layer
        
        # Log activity
        WorkerActivity.log_activity(
            worker=self.worker,
            activity_type='accepted',
            description=f"Accepted assignment for {self.service_request.title}",
            service_request=self.service_request
        )
        
        return True
    
    def reject_assignment(self, reason=''):
        """Worker rejects this assignment"""
        self.worker_accepted = False
        self.worker_response_at = timezone.now()
        self.worker_rejection_reason = reason
        self.status = 'rejected'
        self.save()
        
        # AUTO-UPDATE: Set worker to available if no other active jobs
        if not self._worker_has_other_active_jobs():
            self.worker.availability = 'available'
            self.worker.save()
        
        # Note: Notifications are handled in the API view layer
        
        # Log activity
        WorkerActivity.log_activity(
            worker=self.worker,
            activity_type='rejected',
            description=f"Rejected assignment: {reason}",
            service_request=self.service_request
        )
        
        return True
    
    def mark_completed(self, completion_notes=''):
        """Worker marks their assignment as completed"""
        self.work_completed_at = timezone.now()
        self.status = 'completed'
        self.completion_notes = completion_notes
        self.save()
        
        # Note: Notifications are handled in the API view layer
        
        # Update worker completed jobs count and credit what they earned.
        # total_earnings was never incremented anywhere in the service-request
        # flow, so a worker's lifetime earnings sat at zero however much work
        # they finished. F() rather than read-modify-write, so two devices
        # completing at once cannot lose one of the increments.
        payment = Decimal(str(self.worker_payment or '0.00'))
        WorkerProfile.objects.filter(pk=self.worker_id).update(
            completed_jobs=models.F('completed_jobs') + 1,
            total_earnings=models.F('total_earnings') + payment,
        )
        self.worker.refresh_from_db(fields=['completed_jobs', 'total_earnings'])

        # AUTO-UPDATE: Set worker to available if no other active jobs
        if not self._worker_has_other_active_jobs():
            self.worker.availability = 'available'
            self.worker.save(update_fields=['availability'])

        # Credit the recruiting agent's commission, if this worker has one.
        # AgentProfile.total_commission_earned previously existed but was
        # never actually incremented anywhere in the codebase.
        if self.worker.agent_id:
            agent = self.worker.agent
            commission = (self.worker_payment * agent.commission_rate / 100).quantize(Decimal('0.01'))
            agent.total_commission_earned += commission
            agent.save(update_fields=['total_commission_earned'])

        # Check if all assignments are completed
        self._check_all_completed()
        
        # Note: Notifications are handled in the API view layer
        
        # Log activity
        WorkerActivity.log_activity(
            worker=self.worker,
            activity_type='completed',
            description=f"Completed work for {self.service_request.title}",
            service_request=self.service_request,
            amount_earned=self.worker_payment
        )
        
        return True
    
    def _update_main_request_status(self):
        """Update main service request status based on assignments"""
        sr = self.service_request

        # If any worker accepted, update main request to "in_progress". This
        # is called right after self.status is set to 'accepted' (see
        # accept_assignment() above) - checking for 'in_progress' here never
        # matched, so the main request silently stayed on "assigned" forever
        # even once a worker was actively working on it.
        if self.status == 'accepted':
            if sr.status == 'pending' or sr.status == 'assigned':
                sr.status = 'in_progress'
                sr.save()
    
    def _check_all_completed(self):
        """Check if all assignments are completed and update main request"""
        sr = self.service_request
        
        # Get all assignments for this service request
        all_assignments = ServiceRequestAssignment.objects.filter(service_request=sr)
        completed_count = all_assignments.filter(status='completed').count()
        total_count = all_assignments.count()
        
        # If all assignments completed, mark main request as completed
        if completed_count == total_count and total_count > 0:
            sr.status = 'completed'
            sr.work_completed_at = timezone.now()
            sr.save()
            
            # Notify client that all work is done
            from worker_connect.notification_service import NotificationService
            NotificationService.notify_service_completed(sr)
    
    def calculate_payment(self):
        """
        What this worker earns for the request.

        Pricing is per request, so a worker earns the category amount once -
        not multiplied by duration. The platform's service_fee is the
        marketplace's margin and is deliberately never part of worker income.
        """
        self.worker_payment = Decimal(str(self.service_request.daily_rate or '0.00'))
        self.save(update_fields=['worker_payment', 'updated_at'])
        return self.worker_payment
    
    def _worker_has_other_active_jobs(self):
        """Check if worker has other active assignments (excluding this one)"""
        active_count = ServiceRequestAssignment.objects.filter(
            worker=self.worker,
            status__in=['pending', 'accepted', 'in_progress']
        ).exclude(id=self.id).count()
        return active_count > 0
