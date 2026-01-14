"""
Models for Client Portal.
"""
import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class Client(models.Model):
    """
    Client profile for the client portal.
    Links to invoices via email address across multiple companies.
    """
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)

    # Profile data (can be updated by client)
    preferred_name = models.CharField(max_length=255, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.preferred_name or self.name or self.email

    def get_display_name(self):
        """Get the best available name for display."""
        return self.preferred_name or self.name or self.email.split('@')[0]

    def get_invoices(self):
        """Get all invoices for this client across all companies."""
        from apps.invoices.models import Invoice
        return Invoice.objects.filter(
            client_email__iexact=self.email
        ).select_related('company').order_by('-created_at')

    def get_companies(self):
        """Get all companies this client has invoices from."""
        from apps.companies.models import Company
        company_ids = self.get_invoices().values_list('company_id', flat=True).distinct()
        return Company.objects.filter(id__in=company_ids)

    def get_total_outstanding(self):
        """Get total outstanding amount across all invoices."""
        from django.db.models import Sum
        result = self.get_invoices().filter(
            status__in=['sent', 'overdue']
        ).aggregate(total=Sum('total'))
        return result['total'] or 0

    def get_total_paid(self):
        """Get total amount paid across all invoices."""
        from django.db.models import Sum
        result = self.get_invoices().filter(
            status='paid'
        ).aggregate(total=Sum('total'))
        return result['total'] or 0


class MagicLinkToken(models.Model):
    """
    Magic link token for passwordless client authentication.
    Short-lived tokens sent via email.
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='magic_link_tokens'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Optional: link to specific invoice for context
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='magic_link_tokens'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['client', 'expires_at']),
        ]

    def __str__(self):
        return f"Magic link for {self.client.email}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            expiry_minutes = getattr(settings, 'CLIENT_PORTAL_MAGIC_LINK_EXPIRY_MINUTES', 30)
            self.expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if token is still valid (not expired and not used)."""
        return (
            self.used_at is None and
            self.expires_at > timezone.now()
        )

    def mark_used(self, request=None):
        """Mark token as used and capture request info."""
        self.used_at = timezone.now()
        if request:
            self.ip_address = self.get_client_ip(request)
            self.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        self.save(update_fields=['used_at', 'ip_address', 'user_agent'])

    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class ClientSession(models.Model):
    """
    Client portal session - longer lived than magic link tokens.
    Created when a magic link is used.
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Source tracking
    magic_link_token = models.ForeignKey(
        MagicLinkToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['client', 'is_active']),
        ]

    def __str__(self):
        return f"Session for {self.client.email}"

    def save(self, *args, **kwargs):
        if not self.session_token:
            self.session_token = secrets.token_urlsafe(48)
        if not self.expires_at:
            expiry_days = getattr(settings, 'CLIENT_PORTAL_SESSION_EXPIRY_DAYS', 30)
            self.expires_at = timezone.now() + timedelta(days=expiry_days)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if session is still valid."""
        return (
            self.is_active and
            self.expires_at > timezone.now()
        )

    def refresh(self):
        """Refresh session expiration."""
        expiry_days = getattr(settings, 'CLIENT_PORTAL_SESSION_EXPIRY_DAYS', 30)
        self.expires_at = timezone.now() + timedelta(days=expiry_days)
        self.save(update_fields=['expires_at', 'last_activity'])

    def invalidate(self):
        """Invalidate this session."""
        self.is_active = False
        self.save(update_fields=['is_active'])


class ClientPayment(models.Model):
    """
    Track payments made through the client portal.
    """
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.CASCADE,
        related_name='client_payments'
    )

    # Stripe Connect details
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, unique=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True)

    # Payment details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Platform fee (optional)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['invoice']),
            models.Index(fields=['stripe_checkout_session_id']),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.invoice.invoice_number}"

    def complete(self):
        """Mark payment as completed and update invoice."""
        self.status = 'succeeded'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])

        # Mark invoice as paid
        self.invoice.status = 'paid'
        self.invoice.paid_at = timezone.now()
        self.invoice.save(update_fields=['status', 'paid_at'])
