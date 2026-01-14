"""
Custom User model for InvoiceKits.
"""
import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """Extended user model with subscription and API features."""

    SUBSCRIPTION_TIERS = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
    ]

    email = models.EmailField(unique=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TIERS,
        default='free'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('canceled', 'Canceled'),
            ('past_due', 'Past Due'),
            ('trialing', 'Trialing'),
            ('inactive', 'Inactive'),
        ],
        default='inactive'
    )
    api_key = models.CharField(max_length=64, unique=True, blank=True, null=True)
    api_key_created_at = models.DateTimeField(blank=True, null=True)

    # Usage tracking (for subscribers)
    invoices_created_this_month = models.PositiveIntegerField(default=0)
    api_calls_this_month = models.PositiveIntegerField(default=0)
    usage_reset_date = models.DateField(default=timezone.now)

    # Credit system (for pay-as-you-go users)
    credits_balance = models.PositiveIntegerField(default=0)  # Purchased credits
    free_credits_remaining = models.PositiveIntegerField(default=5)  # Lifetime free credits
    total_credits_purchased = models.PositiveIntegerField(default=0)  # Lifetime stats

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def generate_api_key(self):
        """Generate a new API key for the user."""
        self.api_key = f"inv_{secrets.token_urlsafe(32)}"
        self.api_key_created_at = timezone.now()
        self.save(update_fields=['api_key', 'api_key_created_at'])
        return self.api_key

    # Credit system methods
    def is_active_subscriber(self):
        """Check if user has an active paid subscription."""
        return (
            self.subscription_tier != 'free' and
            self.subscription_status == 'active'
        )

    def get_available_credits(self):
        """Get total available credits (free + purchased)."""
        return self.free_credits_remaining + self.credits_balance

    def deduct_credit(self):
        """Deduct one credit, prioritizing free credits first."""
        if self.free_credits_remaining > 0:
            self.free_credits_remaining -= 1
            self.save(update_fields=['free_credits_remaining'])
            return True
        elif self.credits_balance > 0:
            self.credits_balance -= 1
            self.save(update_fields=['credits_balance'])
            return True
        return False

    def add_credits(self, amount):
        """Add purchased credits to balance."""
        self.credits_balance += amount
        self.total_credits_purchased += amount
        self.save(update_fields=['credits_balance', 'total_credits_purchased'])

    def reset_monthly_usage(self):
        """Reset monthly usage counters."""
        self.invoices_created_this_month = 0
        self.api_calls_this_month = 0
        self.usage_reset_date = timezone.now().date()
        self.save(update_fields=[
            'invoices_created_this_month',
            'api_calls_this_month',
            'usage_reset_date'
        ])

    def check_usage_reset(self):
        """Check if usage should be reset (new month)."""
        today = timezone.now().date()
        if self.usage_reset_date.month != today.month or self.usage_reset_date.year != today.year:
            self.reset_monthly_usage()

    def can_create_invoice(self):
        """Check if user can create another invoice.

        For active subscribers: Uses monthly quota from subscription tier.
        For credit users (free tier or inactive subscription): Uses credits.
        """
        from django.conf import settings

        # Active subscribers use monthly quota
        if self.is_active_subscriber():
            self.check_usage_reset()
            tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
            limit = tier_config.get('invoices_per_month', 0)

            if limit == -1:  # Unlimited
                return True
            return self.invoices_created_this_month < limit

        # Credit users (free tier or canceled subscription) use credits
        return self.get_available_credits() > 0

    def increment_invoice_count(self):
        """Increment invoice count (subscribers) or deduct credit (credit users)."""
        # Active subscribers use monthly quota
        if self.is_active_subscriber():
            self.check_usage_reset()
            self.invoices_created_this_month += 1
            self.save(update_fields=['invoices_created_this_month'])
        else:
            # Credit users deduct from credits
            self.deduct_credit()

    def can_make_api_call(self):
        """Check if user can make another API call this month."""
        from django.conf import settings
        self.check_usage_reset()

        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        if not tier_config.get('api_access', False):
            return False

        limit = tier_config.get('api_calls_per_month', 0)
        if limit == -1:  # Unlimited
            return True
        return self.api_calls_this_month < limit

    def increment_api_call_count(self):
        """Increment the API call count for the month."""
        self.check_usage_reset()
        self.api_calls_this_month += 1
        self.save(update_fields=['api_calls_this_month'])

    def get_available_templates(self):
        """Get list of templates available to this user."""
        from django.conf import settings

        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        templates = tier_config.get('templates', ['clean_slate'])

        if templates == 'all':
            return list(settings.INVOICE_TEMPLATES.keys())
        return templates

    def has_batch_upload(self):
        """Check if user has batch upload feature."""
        from django.conf import settings
        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        return tier_config.get('batch_upload', False)

    def has_api_access(self):
        """Check if user has API access."""
        from django.conf import settings
        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        return tier_config.get('api_access', False)

    def shows_watermark(self):
        """Check if invoices should show watermark.

        Watermarks shown only for users using free credits (never purchased).
        Subscribers and users who have purchased credits get no watermark.
        """
        # Active subscribers never see watermarks
        if self.is_active_subscriber():
            return False
        # Users who have purchased credits don't see watermarks
        if self.total_credits_purchased > 0:
            return False
        # Users who have purchased credits balance don't see watermarks
        if self.credits_balance > 0:
            return False
        # Only show watermark for users on free credits only
        return True

    def get_usage_percentage(self):
        """Get percentage of invoice limit used.

        For subscribers: percentage of monthly quota used.
        For credit users: returns 0 (credits don't have a percentage concept).
        """
        from django.conf import settings

        # Credit users don't have a percentage-based limit
        if not self.is_active_subscriber():
            return 0

        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        limit = tier_config.get('invoices_per_month', 0)

        if limit == -1:
            return 0
        if limit == 0:
            return 100
        return min(100, int((self.invoices_created_this_month / limit) * 100))

    def has_recurring_invoices(self):
        """Check if user has recurring invoices feature."""
        from django.conf import settings
        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        return tier_config.get('recurring_invoices', False)

    def can_create_recurring_invoice(self):
        """Check if user can create another recurring invoice."""
        from django.conf import settings
        if not self.has_recurring_invoices():
            return False

        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        max_recurring = tier_config.get('max_recurring', 0)

        if max_recurring == -1:  # Unlimited
            return True

        # Get count from user's company recurring invoices
        from apps.invoices.models import RecurringInvoice
        try:
            company = self.companies.first()
            if not company:
                return False
            current_count = RecurringInvoice.objects.filter(
                company=company,
                status__in=['active', 'paused']
            ).count()
            return current_count < max_recurring
        except Exception:
            return False

    def get_recurring_invoice_limit(self):
        """Get the max recurring invoices allowed for this user's tier."""
        from django.conf import settings
        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        return tier_config.get('max_recurring', 0)

    # Team seat methods
    def get_team_seat_limit(self):
        """Get the max team seats allowed for this user's tier."""
        from django.conf import settings
        tier_config = settings.SUBSCRIPTION_TIERS.get(self.subscription_tier, {})
        return tier_config.get('team_seats', 0)

    def has_team_seats(self):
        """Check if user's tier includes team seats."""
        return self.get_team_seat_limit() > 0

    def get_company(self):
        """Get the company this user belongs to (owned or member of).

        Returns the company the user owns first, then checks team memberships.
        """
        # First check if user owns a company
        owned_company = self.owned_companies.first()
        if owned_company:
            return owned_company

        # Check legacy company field
        if hasattr(self, 'company'):
            try:
                return self.company
            except Exception:
                pass

        # Check if user is a team member
        membership = self.team_memberships.select_related('company').first()
        if membership:
            return membership.company

        return None

    def is_team_admin(self, company=None):
        """Check if user is an admin for the given company (or their own company)."""
        company = company or self.get_company()
        if not company:
            return False
        return company.is_admin(self)

    def is_company_owner(self, company=None):
        """Check if user is the owner of the given company."""
        company = company or self.get_company()
        if not company:
            return False
        return company.get_effective_owner() == self
