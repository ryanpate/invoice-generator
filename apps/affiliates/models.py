import uuid
import secrets
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_referral_code():
    """Generate a unique 8-character referral code."""
    return secrets.token_urlsafe(6)[:8].upper()


class Affiliate(models.Model):
    """
    Represents a user who has joined the affiliate program.
    Each affiliate gets a unique referral code to share.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='affiliate_profile'
    )
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        default=generate_referral_code
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Payment details
    paypal_email = models.EmailField(blank=True, null=True)

    # Stats (denormalized for performance)
    total_referrals = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} ({self.referral_code})"

    def get_referral_url(self):
        """Get the full referral URL."""
        return f"https://www.invoicekits.com/ref/{self.referral_code}/"

    def approve(self):
        """Approve this affiliate."""
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_at'])

    def update_stats(self):
        """Recalculate stats from related objects."""
        self.total_referrals = self.referrals.count()
        self.total_conversions = self.referrals.filter(converted=True).count()

        commissions = self.commissions.all()
        self.total_earnings = sum(c.amount for c in commissions)
        self.pending_earnings = sum(c.amount for c in commissions.filter(status='pending'))
        self.paid_earnings = sum(c.amount for c in commissions.filter(status='paid'))

        self.save(update_fields=[
            'total_referrals', 'total_conversions',
            'total_earnings', 'pending_earnings', 'paid_earnings'
        ])


class Referral(models.Model):
    """
    Tracks when someone visits the site via a referral link.
    A referral converts when the referred user makes a purchase.
    """
    affiliate = models.ForeignKey(
        Affiliate,
        on_delete=models.CASCADE,
        related_name='referrals'
    )
    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral',
        null=True,
        blank=True
    )

    # Tracking
    visitor_id = models.UUIDField(default=uuid.uuid4, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    landing_page = models.URLField(blank=True)

    # Conversion tracking
    converted = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.referred_user:
            return f"{self.affiliate.referral_code} -> {self.referred_user.email}"
        return f"{self.affiliate.referral_code} -> (visitor {str(self.visitor_id)[:8]})"

    def mark_converted(self):
        """Mark this referral as converted."""
        if not self.converted:
            self.converted = True
            self.converted_at = timezone.now()
            self.save(update_fields=['converted', 'converted_at'])
            self.affiliate.update_stats()


class Commission(models.Model):
    """
    Tracks commission earned by affiliates from referred purchases.
    20% commission on all purchases from referred users.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    affiliate = models.ForeignKey(
        Affiliate,
        on_delete=models.CASCADE,
        related_name='commissions'
    )
    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name='commissions'
    )

    # Transaction details
    purchase_type = models.CharField(max_length=50)  # 'subscription', 'credit_pack', 'template'
    purchase_description = models.CharField(max_length=200)
    purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.20'))  # 20%
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Commission earned

    # Stripe reference
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"${self.amount} commission for {self.affiliate.user.email}"

    def save(self, *args, **kwargs):
        # Calculate commission amount if not set
        if not self.amount:
            self.amount = self.purchase_amount * self.commission_rate
        super().save(*args, **kwargs)

    def mark_paid(self):
        """Mark this commission as paid."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at'])
        self.affiliate.update_stats()


class AffiliateApplication(models.Model):
    """
    Application to join the affiliate program.
    Users must apply and be approved before becoming affiliates.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='affiliate_applications'
    )

    # Application details
    website = models.URLField(blank=True, help_text="Your website or social media profile")
    audience_size = models.CharField(max_length=100, blank=True, help_text="Approximate audience size")
    promotion_methods = models.TextField(help_text="How do you plan to promote InvoiceKits?")

    # Status
    reviewed = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Application from {self.user.email}"

    def approve(self):
        """Approve this application and create an affiliate profile."""
        self.reviewed = True
        self.approved = True
        self.reviewed_at = timezone.now()
        self.save(update_fields=['reviewed', 'approved', 'reviewed_at'])

        # Create affiliate profile
        affiliate, created = Affiliate.objects.get_or_create(user=self.user)
        affiliate.approve()
        return affiliate

    def reject(self, reason=''):
        """Reject this application."""
        self.reviewed = True
        self.approved = False
        self.rejection_reason = reason
        self.reviewed_at = timezone.now()
        self.save(update_fields=['reviewed', 'approved', 'rejection_reason', 'reviewed_at'])
