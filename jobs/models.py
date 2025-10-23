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


class Message(models.Model):
    """Messages between clients and workers"""
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    job = models.ForeignKey(JobRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}"
