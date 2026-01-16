"""
Invoice models for InvoiceKits.
"""
import uuid
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
    invoice_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Optional name/description for this invoice (e.g., "Website Redesign Project")'
    )
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

    # Public access token for QR code links
    public_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Unique token for public invoice access'
    )

    # Payment reminders
    reminders_paused = models.BooleanField(
        default=False,
        help_text='Pause automated payment reminders for this invoice'
    )

    # Late fees
    late_fees_paused = models.BooleanField(
        default=False,
        help_text='Pause automatic late fees for this invoice'
    )
    late_fee_applied = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Amount of late fee applied to this invoice'
    )
    late_fee_applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the late fee was applied'
    )
    original_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original total before late fee was applied'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when invoice was marked as paid'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when invoice was sent to client'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['invoice_number']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track original status for detecting changes in signals
        self._original_status = self.status

    def __str__(self):
        if self.invoice_name:
            return f"{self.invoice_number} - {self.invoice_name}"
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
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])

    def mark_as_paid(self):
        """Mark invoice as paid."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at', 'updated_at'])

    def get_payment_days(self):
        """
        Calculate days between sent and paid.
        Returns None if invoice is not paid or was never sent.
        """
        if self.status != 'paid' or not self.paid_at:
            return None
        # Use sent_at if available, otherwise fall back to invoice_date
        sent_date = self.sent_at.date() if self.sent_at else self.invoice_date
        paid_date = self.paid_at.date()
        return (paid_date - sent_date).days

    def get_public_url(self):
        """Get public URL for this invoice (used in QR codes)."""
        site_url = getattr(settings, 'SITE_URL', 'https://www.invoicekits.com')
        return f"{site_url}/invoice/{self.public_token}/"

    def apply_late_fee(self, fee_amount):
        """
        Apply a late fee to this invoice.

        Args:
            fee_amount: The late fee amount to apply

        Returns:
            bool: True if late fee was applied, False if already applied
        """
        if self.late_fee_applied > 0:
            return False  # Already has a late fee

        # Store original total before applying fee
        if not self.original_total:
            self.original_total = self.total

        # Apply the late fee
        self.late_fee_applied = Decimal(str(fee_amount)).quantize(Decimal('0.01'))
        self.total = self.original_total + self.late_fee_applied
        self.late_fee_applied_at = timezone.now()

        self.save(update_fields=[
            'late_fee_applied',
            'late_fee_applied_at',
            'original_total',
            'total',
            'updated_at'
        ])

        return True

    def remove_late_fee(self):
        """
        Remove the late fee from this invoice.

        Returns:
            bool: True if late fee was removed, False if no late fee to remove
        """
        if self.late_fee_applied == 0:
            return False

        # Restore original total
        if self.original_total:
            self.total = self.original_total

        self.late_fee_applied = Decimal('0.00')
        self.late_fee_applied_at = None

        self.save(update_fields=[
            'late_fee_applied',
            'late_fee_applied_at',
            'total',
            'updated_at'
        ])

        return True

    def can_apply_late_fee(self):
        """
        Check if a late fee can be applied to this invoice.

        Returns:
            bool: True if late fee can be applied
        """
        # Don't apply if already has late fee
        if self.late_fee_applied > 0:
            return False

        # Don't apply if paused
        if self.late_fees_paused:
            return False

        # Only apply to unpaid invoices
        if self.status in ['paid', 'cancelled', 'draft']:
            return False

        return True


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


class RecurringInvoice(models.Model):
    """Recurring invoice template that auto-generates invoices on schedule."""

    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='recurring_invoices'
    )

    # Internal name for this recurring invoice
    name = models.CharField(
        max_length=255,
        help_text='Internal name (e.g., "Monthly Retainer - Acme Corp")'
    )

    # Client information (copied to generated invoices)
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField(blank=True)

    # Schedule
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='monthly'
    )
    start_date = models.DateField()
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text='Leave blank for indefinite recurring'
    )
    next_run_date = models.DateField()

    # Invoice settings (copied to generated invoices)
    currency = models.CharField(
        max_length=3,
        choices=settings.CURRENCIES,
        default='USD'
    )
    payment_terms = models.CharField(
        max_length=20,
        choices=settings.PAYMENT_TERMS,
        default='net_30'
    )
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    template_style = models.CharField(max_length=50, default='clean_slate')
    notes = models.TextField(blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Tracking
    invoices_generated = models.PositiveIntegerField(default=0)
    last_generated_at = models.DateTimeField(blank=True, null=True)
    last_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='recurring_source'
    )

    # Notification settings
    send_email_on_generation = models.BooleanField(
        default=True,
        help_text='Email owner when invoice is generated'
    )
    auto_send_to_client = models.BooleanField(
        default=False,
        help_text='Automatically send invoice to client email'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['next_run_date', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"

    def save(self, *args, **kwargs):
        # Set next_run_date to start_date if not set
        if not self.next_run_date:
            self.next_run_date = self.start_date
        super().save(*args, **kwargs)

    def calculate_next_run_date(self):
        """Calculate the next run date based on frequency."""
        frequency_deltas = {
            'weekly': relativedelta(weeks=1),
            'biweekly': relativedelta(weeks=2),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'yearly': relativedelta(years=1),
        }
        delta = frequency_deltas.get(self.frequency, relativedelta(months=1))
        return self.next_run_date + delta

    def should_run_today(self):
        """Check if this recurring invoice should run today."""
        if self.status != 'active':
            return False
        if self.end_date and timezone.now().date() > self.end_date:
            return False
        return self.next_run_date <= timezone.now().date()

    def generate_invoice(self):
        """Generate an invoice from this recurring template."""
        # Generate invoice number
        today = timezone.now()
        prefix = today.strftime('%Y%m')
        count = Invoice.objects.filter(
            company=self.company,
            invoice_number__startswith=f'INV-{prefix}'
        ).count() + 1
        invoice_number = f'INV-{prefix}-{count:04d}'

        # Create the invoice
        invoice = Invoice.objects.create(
            company=self.company,
            invoice_number=invoice_number,
            invoice_name=self.name,
            status='draft',
            client_name=self.client_name,
            client_email=self.client_email,
            client_phone=self.client_phone,
            client_address=self.client_address,
            invoice_date=timezone.now().date(),
            payment_terms=self.payment_terms,
            currency=self.currency,
            tax_rate=self.tax_rate,
            template_style=self.template_style,
            notes=self.notes,
        )

        # Copy line items
        for recurring_item in self.line_items.all():
            LineItem.objects.create(
                invoice=invoice,
                description=recurring_item.description,
                quantity=recurring_item.quantity,
                rate=recurring_item.rate,
                order=recurring_item.order,
            )

        # Update tracking
        self.invoices_generated += 1
        self.last_generated_at = timezone.now()
        self.last_invoice = invoice
        self.next_run_date = self.calculate_next_run_date()

        # Check if we've passed the end date
        if self.end_date and self.next_run_date > self.end_date:
            self.status = 'cancelled'

        self.save()

        return invoice

    def pause(self):
        """Pause this recurring invoice."""
        self.status = 'paused'
        self.save(update_fields=['status', 'updated_at'])

    def resume(self):
        """Resume this recurring invoice."""
        self.status = 'active'
        # If next_run_date is in the past, set it to today
        if self.next_run_date < timezone.now().date():
            self.next_run_date = timezone.now().date()
        self.save(update_fields=['status', 'next_run_date', 'updated_at'])

    def cancel(self):
        """Cancel this recurring invoice."""
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])


class RecurringLineItem(models.Model):
    """Line item for recurring invoice template."""

    recurring_invoice = models.ForeignKey(
        RecurringInvoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.rate})"

    @property
    def amount(self):
        """Calculate line item amount."""
        return (self.quantity * self.rate).quantize(Decimal('0.01'))


class PaymentReminderSettings(models.Model):
    """Company-level settings for automated payment reminders."""

    company = models.OneToOneField(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='reminder_settings'
    )

    # Master toggle
    reminders_enabled = models.BooleanField(
        default=False,
        help_text='Enable automated payment reminders'
    )

    # Schedule (which reminders to send)
    remind_3_days_before = models.BooleanField(default=True)
    remind_1_day_before = models.BooleanField(default=True)
    remind_on_due_date = models.BooleanField(default=True)
    remind_3_days_after = models.BooleanField(default=True)
    remind_7_days_after = models.BooleanField(default=True)
    remind_14_days_after = models.BooleanField(default=True)

    # CC options
    cc_business_owner = models.BooleanField(
        default=False,
        help_text='Send a copy of reminders to business owner'
    )

    # Custom messages (optional)
    custom_message_before = models.TextField(
        blank=True,
        help_text='Custom message for reminders before due date'
    )
    custom_message_due = models.TextField(
        blank=True,
        help_text='Custom message for reminder on due date'
    )
    custom_message_overdue = models.TextField(
        blank=True,
        help_text='Custom message for reminders after due date'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Reminder Settings'
        verbose_name_plural = 'Payment Reminder Settings'

    def __str__(self):
        status = 'enabled' if self.reminders_enabled else 'disabled'
        return f"Reminders for {self.company.name} ({status})"

    def get_enabled_days(self):
        """Return list of days offset for enabled reminders."""
        days = []
        if self.remind_3_days_before:
            days.append(-3)
        if self.remind_1_day_before:
            days.append(-1)
        if self.remind_on_due_date:
            days.append(0)
        if self.remind_3_days_after:
            days.append(3)
        if self.remind_7_days_after:
            days.append(7)
        if self.remind_14_days_after:
            days.append(14)
        return days


class PaymentReminderLog(models.Model):
    """Track sent payment reminders to prevent duplicates."""

    REMINDER_TYPES = [
        ('before', 'Before Due Date'),
        ('due', 'On Due Date'),
        ('overdue', 'Overdue'),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='reminder_logs'
    )
    days_offset = models.IntegerField(
        help_text='Days relative to due date (negative=before, 0=on due, positive=after)'
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPES
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    recipient_email = models.EmailField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Payment Reminder Log'
        verbose_name_plural = 'Payment Reminder Logs'
        unique_together = ['invoice', 'days_offset']
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['invoice', 'days_offset']),
        ]

    def __str__(self):
        return f"Reminder for {self.invoice.invoice_number} ({self.days_offset:+d} days)"


class LateFeeLog(models.Model):
    """Track applied late fees for audit purposes."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='late_fee_logs'
    )
    fee_type = models.CharField(
        max_length=20,
        help_text='Type of fee applied (flat or percentage)'
    )
    fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount of late fee applied'
    )
    days_overdue = models.PositiveIntegerField(
        help_text='Days past due date when fee was applied'
    )
    invoice_total_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Invoice total before late fee'
    )
    invoice_total_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Invoice total after late fee'
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    applied_by = models.CharField(
        max_length=50,
        default='system',
        help_text='Who/what applied the fee (system or manual)'
    )

    class Meta:
        verbose_name = 'Late Fee Log'
        verbose_name_plural = 'Late Fee Logs'
        ordering = ['-applied_at']

    def __str__(self):
        return f"Late fee ${self.fee_amount} on {self.invoice.invoice_number}"
