"""
Worker portfolio models and service for Worker Connect.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import os
import uuid


def portfolio_upload_path(instance, filename):
    """Generate upload path for portfolio media."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('portfolio', str(instance.worker.id), filename)


class PortfolioItem(models.Model):
    """
    Portfolio item for showcasing worker's past work.
    """
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('link', 'External Link'),
    ]
    
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='portfolio_items'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='image')
    
    # Media fields
    media_file = models.FileField(upload_to=portfolio_upload_path, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='portfolio/thumbnails/', blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    
    # Metadata
    category = models.ForeignKey(
        'workers.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    tags = models.JSONField(default=list, blank=True)
    
    # Job reference (optional)
    related_job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', 'display_order', '-created_at']
        
    def __str__(self):
        return f"{self.worker} - {self.title}"


class PortfolioService:
    """
    Service class for managing portfolio items.
    """
    
    @staticmethod
    def add_portfolio_item(worker, title, description='', media_type='image',
                           media_file=None, external_url=None, category=None,
                           tags=None, related_job=None, is_public=True):
        """
        Add a portfolio item for a worker.
        """
        item = PortfolioItem.objects.create(
            worker=worker,
            title=title,
            description=description,
            media_type=media_type,
            media_file=media_file,
            external_url=external_url,
            category=category,
            tags=tags or [],
            related_job=related_job,
            is_public=is_public,
        )
        return item
    
    @staticmethod
    def get_worker_portfolio(worker, public_only=True, category=None):
        """
        Get portfolio items for a worker.
        """
        queryset = PortfolioItem.objects.filter(worker=worker)
        
        if public_only:
            queryset = queryset.filter(is_public=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    @staticmethod
    def get_featured_items(worker, limit=5):
        """
        Get featured portfolio items for a worker.
        """
        return PortfolioItem.objects.filter(
            worker=worker,
            is_featured=True,
            is_public=True
        )[:limit]
    
    @staticmethod
    def update_portfolio_item(item_id, worker, **kwargs):
        """
        Update a portfolio item.
        """
        try:
            item = PortfolioItem.objects.get(id=item_id, worker=worker)
        except PortfolioItem.DoesNotExist:
            return None
        
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        item.save()
        return item
    
    @staticmethod
    def delete_portfolio_item(item_id, worker):
        """
        Delete a portfolio item.
        """
        try:
            item = PortfolioItem.objects.get(id=item_id, worker=worker)
            item.delete()
            return True
        except PortfolioItem.DoesNotExist:
            return False
    
    @staticmethod
    def reorder_items(worker, item_order):
        """
        Reorder portfolio items.
        
        Args:
            worker: Worker instance
            item_order: List of item IDs in desired order
        """
        for index, item_id in enumerate(item_order):
            PortfolioItem.objects.filter(
                id=item_id,
                worker=worker
            ).update(display_order=index)
    
    @staticmethod
    def set_featured(item_id, worker, is_featured=True):
        """
        Set or unset an item as featured.
        """
        try:
            item = PortfolioItem.objects.get(id=item_id, worker=worker)
            item.is_featured = is_featured
            item.save()
            return item
        except PortfolioItem.DoesNotExist:
            return None
    
    @staticmethod
    def get_portfolio_stats(worker):
        """
        Get portfolio statistics for a worker.
        """
        items = PortfolioItem.objects.filter(worker=worker)
        
        return {
            'total_items': items.count(),
            'public_items': items.filter(is_public=True).count(),
            'featured_items': items.filter(is_featured=True).count(),
            'by_type': {
                media_type: items.filter(media_type=media_type).count()
                for media_type, _ in PortfolioItem.MEDIA_TYPE_CHOICES
            },
        }
