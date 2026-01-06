"""
Billing models for subscription management.
"""
from django.db import models
from django.conf import settings


class UsageRecord(models.Model):
    """Monthly usage tracking for users."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    month = models.DateField(help_text='First day of the billing month')
    invoices_created = models.PositiveIntegerField(default=0)
    api_calls = models.PositiveIntegerField(default=0)
    batch_uploads = models.PositiveIntegerField(default=0)
    pdf_downloads = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'month']
        ordering = ['-month']

    def __str__(self):
        return f"{self.user.email} - {self.month.strftime('%B %Y')}"


class PaymentHistory(models.Model):
    """Record of payments for reference."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Payment histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ${self.amount} - {self.status}"
