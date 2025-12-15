from django.db import models
from accounts.models import User
from workers.models import WorkerProfile, Category


class JobRequest(models.Model):
    """Job requests posted by clients"""
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    URGENCY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_requests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='jobs')
    
    # Job details
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_days = models.IntegerField(help_text="Estimated duration in days")
    start_date = models.DateField(null=True, blank=True)
    workers_needed = models.PositiveIntegerField(default=1, help_text="Number of workers needed for this job")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    
    # Assignment - Multiple workers can be assigned
    assigned_workers = models.ManyToManyField(
        WorkerProfile,
        blank=True,
        related_name='assigned_jobs'
    )
    
    # Keep the old single worker field for compatibility (deprecated)
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='old_assigned_jobs',
        help_text="Deprecated: Use assigned_workers instead"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.client.username}"
    
    @property
    def application_count(self):
        return self.applications.count()
    
    @property
    def workers_remaining(self):
        """Calculate how many more workers are needed"""
        return max(0, self.workers_needed - self.assigned_workers.count())
    
    @property
    def is_fully_staffed(self):
        """Check if job has enough workers assigned"""
        return self.assigned_workers.count() >= self.workers_needed


class JobApplication(models.Model):
    """Applications from workers for jobs"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    job = models.ForeignKey(JobRequest, on_delete=models.CASCADE, related_name='applications')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField(blank=True)  # Optional text version
    cover_letter_file = models.FileField(upload_to='cover_letters/', blank=True, null=True, help_text="Upload your cover letter (PDF, DOC, DOCX)")
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['job', 'worker']
    
    def __str__(self):
        return f"{self.worker.user.username} applied for {self.job.title}"


class DirectHireRequest(models.Model):
    """Direct hire/booking requests - instant worker requests"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    DURATION_TYPE_CHOICES = (
        ('hours', 'Hours'),
        ('days', 'Days'),
    )
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_hire_requests')
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='direct_requests')
    
    # Job details
    title = models.CharField(max_length=200, help_text="Brief description of work")
    description = models.TextField(help_text="Detailed work description")
    location = models.CharField(max_length=255, help_text="Where the work will be done")
    
    # Duration
    duration_type = models.CharField(max_length=10, choices=DURATION_TYPE_CHOICES, default='hours')
    duration_value = models.PositiveIntegerField(help_text="Number of hours or days")
    start_datetime = models.DateTimeField(help_text="When should the work start?")
    
    # Payment
    offered_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Offered hourly/daily rate")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total estimated amount")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Response
    worker_response_message = models.TextField(blank=True, help_text="Worker's response/reason")
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    client_rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1-5 stars")
    client_feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['worker', 'status']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.client.get_full_name()} → {self.worker.user.get_full_name()} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total amount
        if self.duration_value and self.offered_rate:
            self.total_amount = self.duration_value * self.offered_rate
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if request is still active"""
        return self.status in ['pending', 'accepted']
    
    @property
    def duration_display(self):
        """Human-readable duration"""
        if self.duration_type == 'hours':
            return f"{self.duration_value} hour{'s' if self.duration_value > 1 else ''}"
        return f"{self.duration_value} day{'s' if self.duration_value > 1 else ''}"


class Message(models.Model):
    """Messages between clients and workers"""
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    job = models.ForeignKey(JobRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    direct_hire = models.ForeignKey(DirectHireRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages', help_text="Link to direct hire request")
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}"
