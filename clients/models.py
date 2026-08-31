from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from workers.models import WorkerProfile


class ClientProfile(models.Model):
    """Extended profile for clients"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True, help_text="Brief introduction about the client")
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Tanzania')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Statistics
    total_jobs_posted = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_spent = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def recalculate_totals(self, save=True):
        """Recompute this client's job and spend totals from their requests.

        These were kept by a += in one of the four places a booking can be
        created, so a client who booked through the mobile app or either API
        never had them move: all three live clients showed 0 jobs and 0
        spent while every one of them had posted and paid. Recomputing
        rather than incrementing means it cannot drift again, and it is
        idempotent however many times it runs.
        """
        from django.db.models import Sum
        from jobs.service_request_models import ServiceRequest

        requests = ServiceRequest.objects.filter(client=self.user)
        self.total_jobs_posted = requests.count()
        self.total_spent = requests.filter(payment_status='paid').aggregate(
            total=Sum('total_price'))['total'] or 0
        if save:
            self.save(update_fields=['total_jobs_posted', 'total_spent'])
        return self.total_jobs_posted, self.total_spent

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


class PaymentTransaction(models.Model):
    """
    A payment reference issued by the payment endpoint.

    The service-request endpoints used to mark a request `paid` purely because
    the caller supplied a `payment_transaction_id` string - any string. A client
    could declare its own booking paid. References are now recorded here when
    the payment endpoint issues them, and a request can only be marked paid by
    presenting a reference that this server issued, to this client, for the
    right amount, and that has not already been used.

    The same shape is what a real gateway integration needs: verify the
    provider's reference before trusting it, and never accept the same one
    twice.
    """

    METHOD_CHOICES = (
        ('card', 'Card'),
        ('mpesa', 'Mobile Money'),
    )

    reference = models.CharField(max_length=64, unique=True, db_index=True)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payment_transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    is_demo = models.BooleanField(
        default=True,
        help_text="True while payments are simulated; a real gateway sets this False"
    )
    consumed_by = models.OneToOneField(
        'jobs.ServiceRequest', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_reference',
        help_text="The request this reference paid for, once redeemed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['client', '-created_at']),
        ]

    def __str__(self):
        state = 'used' if self.consumed_by_id else 'unused'
        return f"{self.reference} ({self.amount}, {state})"

    @property
    def is_consumed(self):
        return self.consumed_by_id is not None

    @classmethod
    def redeem(cls, reference, client, expected_amount=None):
        """
        Look up an unused reference belonging to this client.

        Returns the row, or None when the reference is unknown, belongs to
        someone else, has already been used, or is for a different amount.
        """
        if not reference:
            return None
        try:
            txn = cls.objects.get(reference=reference, client=client)
        except cls.DoesNotExist:
            return None
        if txn.is_consumed:
            return None
        if expected_amount is not None and txn.amount != expected_amount:
            return None
        return txn

