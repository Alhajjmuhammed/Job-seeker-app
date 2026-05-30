"""
Invoice generation for Worker Connect.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from decimal import Decimal
import uuid
import hashlib


class Invoice(models.Model):
    """
    Invoice model for completed jobs.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Parties
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='invoices_issued'
    )
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='invoices_received'
    )
    
    # Job reference
    job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices'
    )
    
    # Invoice details
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
        
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    def calculate_total(self):
        """Calculate total from subtotal, tax, and discount."""
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount - self.discount
        return self.total


class InvoiceItem(models.Model):
    """
    Line items for an invoice.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.description} - {self.total}"


class InvoiceService:
    """
    Service class for invoice operations.
    """
    
    @staticmethod
    def generate_invoice_number():
        """Generate a unique invoice number."""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_part = uuid.uuid4().hex[:6].upper()
        return f"INV-{timestamp}-{random_part}"
    
    @staticmethod
    def create_invoice(worker, client, job, items, tax_rate=0, 
                       discount=0, notes='', terms='', due_days=30):
        """
        Create an invoice for a completed job.
        
        Args:
            worker: Worker instance
            client: Client instance
            job: JobRequest instance
            items: List of dicts with description, quantity, unit_price
            tax_rate: Tax percentage (default 0)
            discount: Discount amount (default 0)
            notes: Optional notes
            terms: Payment terms
            due_days: Days until due (default 30)
        """
        # Calculate subtotal
        subtotal = sum(
            Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
            for item in items
        )
        
        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number=InvoiceService.generate_invoice_number(),
            worker=worker,
            client=client,
            job=job,
            description=f"Invoice for Job #{job.id}" if job else "Service Invoice",
            subtotal=subtotal,
            tax_rate=Decimal(str(tax_rate)),
            discount=Decimal(str(discount)),
            total=0,  # Will be calculated
            due_date=timezone.now().date() + timezone.timedelta(days=due_days),
            notes=notes,
            terms=terms or "Payment due within 30 days of invoice date.",
        )
        
        # Calculate total
        invoice.calculate_total()
        invoice.save()
        
        # Create line items
        for item in items:
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item['description'],
                quantity=Decimal(str(item['quantity'])),
                unit_price=Decimal(str(item['unit_price'])),
                total=Decimal(str(item['quantity'])) * Decimal(str(item['unit_price'])),
            )
        
        return invoice
    
    @staticmethod
    def get_invoice(invoice_id, user):
        """
        Get an invoice by ID, checking permissions.
        """
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            
            # Check if user has access
            if hasattr(user, 'worker_profile'):
                if invoice.worker != user.worker_profile:
                    return None
            elif hasattr(user, 'client_profile'):
                if invoice.client != user.client_profile:
                    return None
            
            return invoice
        except Invoice.DoesNotExist:
            return None
    
    @staticmethod
    def get_worker_invoices(worker, status=None):
        """Get all invoices issued by a worker."""
        queryset = Invoice.objects.filter(worker=worker)
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @staticmethod
    def get_client_invoices(client, status=None):
        """Get all invoices received by a client."""
        queryset = Invoice.objects.filter(client=client)
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @staticmethod
    def mark_as_sent(invoice):
        """Mark invoice as sent."""
        invoice.status = 'sent'
        invoice.save()
        return invoice
    
    @staticmethod
    def mark_as_paid(invoice):
        """Mark invoice as paid."""
        invoice.status = 'paid'
        invoice.paid_date = timezone.now().date()
        invoice.save()
        return invoice
    
    @staticmethod
    def cancel_invoice(invoice):
        """Cancel an invoice."""
        invoice.status = 'cancelled'
        invoice.save()
        return invoice
    
    @staticmethod
    def check_overdue_invoices():
        """Mark overdue invoices."""
        today = timezone.now().date()
        Invoice.objects.filter(
            status='sent',
            due_date__lt=today
        ).update(status='overdue')
    
    @staticmethod
    def generate_pdf(invoice):
        """
        Generate PDF for an invoice.
        Returns PDF bytes.
        """
        try:
            from weasyprint import HTML
            
            # Render HTML template
            html_content = render_to_string('invoices/invoice_template.html', {
                'invoice': invoice,
                'items': invoice.items.all(),
            })
            
            # Generate PDF
            pdf = HTML(string=html_content).write_pdf()
            return pdf
            
        except ImportError:
            # WeasyPrint not installed, return None
            return None
    
    @staticmethod
    def get_invoice_summary(worker=None, client=None):
        """
        Get invoice summary statistics.
        """
        if worker:
            invoices = Invoice.objects.filter(worker=worker)
        elif client:
            invoices = Invoice.objects.filter(client=client)
        else:
            return None
        
        return {
            'total_invoices': invoices.count(),
            'draft': invoices.filter(status='draft').count(),
            'sent': invoices.filter(status='sent').count(),
            'paid': invoices.filter(status='paid').count(),
            'overdue': invoices.filter(status='overdue').count(),
            'cancelled': invoices.filter(status='cancelled').count(),
            'total_amount': sum(inv.total for inv in invoices),
            'paid_amount': sum(inv.total for inv in invoices.filter(status='paid')),
            'outstanding_amount': sum(
                inv.total for inv in invoices.filter(status__in=['sent', 'overdue'])
            ),
        }
