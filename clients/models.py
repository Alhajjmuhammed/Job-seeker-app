from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from workers.models import WorkerProfile


class ClientProfile(models.Model):
    """Extended profile for clients"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Sudan')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Statistics
    total_jobs_posted = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_spent = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['city']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Client Profile"


class Rating(models.Model):
    """Ratings given by clients to workers"""
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='ratings_received')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['client', 'worker']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['worker']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.client.username} rated {self.worker.user.username} - {self.rating} stars"


class Favorite(models.Model):
    """Favorite workers saved by clients"""
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['client', 'worker']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['worker']),
        ]
    
    def __str__(self):
        return f"{self.client.username} favorited {self.worker.user.username}"
