"""
Invoice models for InvoiceKits.
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class Invoice(models.Model):
    """Main invoice model."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='invoices'
    )

    # Invoice details
    invoice_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Client information
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField(blank=True)

    # Dates
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    payment_terms = models.CharField(
        max_length=20,
        choices=settings.PAYMENT_TERMS,
        default='net_30'
    )

    # Financial
    currency = models.CharField(
        max_length=3,
        choices=settings.CURRENCIES,
        default='USD'
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Additional
    notes = models.TextField(blank=True)
    template_style = models.CharField(max_length=50, default='clean_slate')

    # PDF
    pdf_file = models.FileField(
        upload_to='invoices/pdfs/%Y/%m/',
        blank=True,
        null=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"

    def save(self, *args, **kwargs):
        # Calculate due date based on payment terms if not set
        if not self.due_date:
            self.due_date = self.calculate_due_date()

        # Only recalculate totals if this is an existing invoice (has pk)
        # New invoices don't have line_items yet
        if self.pk:
            self.calculate_totals()

        super().save(*args, **kwargs)

    def calculate_due_date(self):
        """Calculate due date based on payment terms."""
        terms_days = {
            'due_on_receipt': 0,
            'net_15': 15,
            'net_30': 30,
            'net_45': 45,
            'net_60': 60,
        }
        days = terms_days.get(self.payment_terms, 30)
        return self.invoice_date + relativedelta(days=days)

    def calculate_totals(self):
        """Calculate subtotal, tax, and total."""
        self.subtotal = sum(item.amount for item in self.line_items.all())
        self.tax_amount = (self.subtotal * self.tax_rate / 100).quantize(Decimal('0.01'))
        self.total = self.subtotal + self.tax_amount - self.discount_amount

    def recalculate_and_save(self):
        """Recalculate totals and save."""
        self.calculate_totals()
        self.save(update_fields=['subtotal', 'tax_amount', 'total', 'updated_at'])

    def get_currency_symbol(self):
        """Get currency symbol."""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'C$',
            'AUD': 'A$',
            'JPY': '¥',
            'INR': '₹',
        }
        return symbols.get(self.currency, self.currency)

    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.status in ['paid', 'cancelled']:
            return False
        return timezone.now().date() > self.due_date

    def mark_as_sent(self):
        """Mark invoice as sent."""
        self.status = 'sent'
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_paid(self):
        """Mark invoice as paid."""
        self.status = 'paid'
        self.save(update_fields=['status', 'updated_at'])


class LineItem(models.Model):
    """Invoice line item."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.rate})"

    def save(self, *args, **kwargs):
        # Calculate amount
        self.amount = (self.quantity * self.rate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

        # Update invoice totals
        self.invoice.recalculate_and_save()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        # Update invoice totals after deletion
        invoice.recalculate_and_save()


class InvoiceBatch(models.Model):
    """Batch invoice processing record."""

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='invoice_batches'
    )
    csv_file = models.FileField(upload_to='invoices/batches/%Y/%m/')
    zip_file = models.FileField(
        upload_to='invoices/batches/%Y/%m/',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    total_invoices = models.PositiveIntegerField(default=0)
    processed_invoices = models.PositiveIntegerField(default=0)
    failed_invoices = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Invoice batches'
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch {self.id} - {self.status}"
