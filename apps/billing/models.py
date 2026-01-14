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


class CreditPurchase(models.Model):
    """Record of credit pack purchases."""

    PURCHASE_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_purchases'
    )
    stripe_session_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    pack_id = models.CharField(max_length=50, help_text='Credit pack identifier (e.g., pack_10)')
    credits_amount = models.PositiveIntegerField(help_text='Number of credits purchased')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PURCHASE_STATUS, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.credits_amount} credits - {self.status}"

    def complete_purchase(self, payment_intent_id=''):
        """Mark purchase as completed and add credits to user."""
        from django.utils import timezone

        if self.status != 'pending':
            return False

        self.status = 'completed'
        self.stripe_payment_intent_id = payment_intent_id
        self.completed_at = timezone.now()
        self.save()

        # Add credits to user
        self.user.add_credits(self.credits_amount)
        return True


class TemplatePurchase(models.Model):
    """Record of premium template purchases."""

    PURCHASE_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='template_purchases'
    )
    stripe_session_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    template_id = models.CharField(
        max_length=50,
        help_text='Template identifier (e.g., executive, bold_modern) or "bundle"'
    )
    is_bundle = models.BooleanField(default=False)
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PURCHASE_STATUS, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        item = "Bundle" if self.is_bundle else self.template_id
        return f"{self.user.email} - {item} - {self.status}"

    def complete_purchase(self, payment_intent_id=''):
        """Mark purchase as completed and unlock template(s) for user."""
        from django.utils import timezone

        if self.status != 'pending':
            return False

        self.status = 'completed'
        self.stripe_payment_intent_id = payment_intent_id
        self.completed_at = timezone.now()
        self.save()

        # Unlock template(s) for user
        if self.is_bundle:
            self.user.unlock_all_premium_templates()
        else:
            self.user.unlock_template(self.template_id)

        return True
