from decimal import Decimal

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
        ('yas', 'Mixx by YAS'),
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

    # --- real gateway money (Mixx by Yas) ---------------------------------
    # consumed_by is a OneToOne that a demo reference usually holds already,
    # so gateway money is linked to its booking here as well. Every row the
    # gateway writes carries the booking it arrived against, whether or not
    # it was applied to it.
    service_request = models.ForeignKey(
        'jobs.ServiceRequest', on_delete=models.SET_NULL, null=True,
        blank=True, related_name='gateway_payments',
        help_text="The booking this gateway money arrived against"
    )
    # Exactly what the gateway knows the payment by - the push ReferenceID
    # with its attempt marker, or the reference the client typed - so a
    # refund can name the original payment without re-deriving it.
    gateway_reference = models.CharField(
        max_length=64, blank=True, default='',
        help_text="The ReferenceID the gateway holds for this payment"
    )
    # Empty when the money paid for the booking. Otherwise it was taken
    # from the client but could not be applied (booking already paid,
    # cancelled, wrong amount...), and it is owed back.
    unapplied_reason = models.TextField(
        blank=True, default='',
        help_text="Why this money was not applied to the booking (owed back)"
    )
    # The wallet the money came from, as the gateway reported it (W2A
    # MSISDN, push CustomerMSISDN, or the number we prompted). A refund
    # goes back here unless somebody records why it should not.
    payer_msisdn = models.CharField(
        max_length=20, blank=True, default='',
        help_text="The wallet this payment came from"
    )
    # False when YAS said money was taken but gave no believable Amount:
    # the amount on this row is then only what we asked for. Such a row is
    # not refundable until a person confirms the amount from the statement.
    amount_confirmed = models.BooleanField(
        default=True,
        help_text="False until a person confirms an amount YAS did not report"
    )
    amount_confirmed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='yas_amounts_confirmed',
        help_text="Who confirmed the amount from the statement"
    )
    amount_note = models.TextField(
        blank=True, default='',
        help_text="The evidence the amount was confirmed on"
    )

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
    def redeemable(cls):
        """Rows a client may present as a booking's payment reference.

        Never money a gateway recorded. A Mixx by Yas receipt is written
        here so it can be reconciled and refunded - and it is often left
        unlinked (consumed_by empty): money that could not be applied, or
        applied money whose booking slot a demo reference already holds.
        Typed in as payment_transaction_id on a new booking, such a row
        used to pay that booking too: free work, or a refundable payment
        spent twice.
        """
        from django.db.models import Q
        return (cls.objects
                .exclude(Q(method='yas') & Q(is_demo=False))
                .filter(service_request__isnull=True, unapplied_reason=''))

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
            txn = cls.redeemable().get(reference=reference, client=client)
        except cls.DoesNotExist:
            return None
        if txn.is_consumed:
            return None
        if expected_amount is not None and txn.amount != expected_amount:
            return None
        return txn

    @classmethod
    def settle(cls, service_request, reference, client):
        """
        Attach a payment reference to a new booking. Returns True if the
        booking is now paid.

        The row is locked so one reference cannot pay for two bookings
        submitted at the same moment. A demo reference (no money moved) is
        recorded on the booking but leaves it 'pending' until an admin
        verifies the client's payment proof - unless DEMO_PAYMENTS_COUNT_AS_PAID
        is switched on, which is only for test environments.
        """
        import logging
        from django.conf import settings
        from django.db import transaction
        from django.utils import timezone

        reference = (reference or '').strip()
        if not reference:
            return False

        with transaction.atomic():
            txn = cls.redeemable().select_for_update().filter(
                reference=reference, client=client, consumed_by__isnull=True
            ).first()
            if txn is None or txn.amount != service_request.total_price:
                logging.getLogger(__name__).warning(
                    "Rejected unverifiable payment reference %r from user %s",
                    reference[:32], client.pk,
                )
                return False

            txn.consumed_by = service_request
            txn.consumed_at = timezone.now()
            txn.save(update_fields=['consumed_by', 'consumed_at'])

            service_request.payment_transaction_id = txn.reference
            update_fields = ['payment_transaction_id', 'updated_at']
            paid = not txn.is_demo or getattr(settings, 'DEMO_PAYMENTS_COUNT_AS_PAID', False)
            if paid:
                service_request.payment_status = 'paid'
                service_request.paid_at = timezone.now()
                update_fields += ['payment_status', 'paid_at']
            service_request.save(update_fields=update_fields)
        return paid



class ClientRefund(models.Model):
    """Money on its way back to a client's Mixx by Yas wallet.

    The Debit Mandate specification calls this Refund Transaction
    (section 4) and will only process one "if the purchase/payment
    transaction was successful" - which is why this row keeps the
    original payment's MFSTransactionID and reference. Without one of
    those two, YAS cannot find the payment being reversed.

    This exists because the push callback now checks the amount YAS
    deducted against what the booking costs. When they disagree, the
    booking is deliberately not marked paid - and that leaves money
    taken from a client with nothing given back. A refund is the way
    out of that, so there has to be one.

    The states, and ``held`` in particular, mean exactly what they mean
    on WorkerPayout: held is not failure, it is "we were not told", and
    nothing automatic touches it.
    """

    STATE_CHOICES = [
        ('pending', 'Waiting to be sent'),
        ('sending', 'Being sent'),
        ('paid', 'Refunded'),
        ('failed', 'Failed'),
        ('held', 'Held - outcome unknown, check the statement'),
    ]

    service_request = models.ForeignKey(
        'jobs.ServiceRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='refunds',
        help_text="The booking being refunded"
    )
    client = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='yas_refunds',
        help_text="The client getting their money back"
    )

    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Amount to send back, in TSh"
    )
    phone_number = models.CharField(
        max_length=20,
        help_text="The wallet it is sent back to, as it was at the time"
    )

    # Ours: "RF" and eighteen digits, twenty characters like the sample
    # reference in their specification.
    reference = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text="The ReferenceID sent to YAS for this refund"
    )
    # One of these two is mandatory on their side. Both are kept when
    # both are known, because which one their gateway accepts is the
    # sort of thing only the first real refund settles.
    mfs_transaction_id = models.CharField(
        max_length=100, blank=True,
        help_text="MFSTransactionID from the original payment callback"
    )
    purchase_reference = models.CharField(
        max_length=64, blank=True,
        help_text="The ReferenceID the original payment was made against"
    )

    state = models.CharField(
        max_length=10, choices=STATE_CHOICES, default='pending', db_index=True
    )
    reason = models.TextField(
        blank=True, help_text="Why this is being refunded"
    )

    # What YAS said, kept verbatim for a dispute.
    yas_reference = models.CharField(max_length=64, blank=True)
    yas_code = models.CharField(max_length=40, blank=True)
    yas_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='yas_refunds_created',
        help_text="The admin who approved this refund"
    )
    # The original gateway payment being reversed. A refund is capped at
    # what that payment actually brought in.
    payment = models.ForeignKey(
        PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='refunds',
        help_text="The original Mixx by Yas payment this reverses"
    )
    # Empty when the money goes back to the wallet it came from.
    destination_note = models.TextField(
        blank=True, default='',
        help_text="Why the destination is not the payer's own wallet"
    )
    # Four-eyes: who pressed send, which must not be who approved it.
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='yas_refunds_sent',
        help_text="The admin who sent this refund"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state', '-created_at']),
            models.Index(fields=['client', '-created_at']),
        ]
        permissions = [
            ('send_clientrefund',
             'Can approve, send and resolve Mixx by Yas refunds'),
        ]

    def __str__(self):
        return f"{self.reference} - TSh {self.amount} back to {self.client} ({self.state})"

    @property
    def needs_a_person(self):
        return self.state == 'held'
