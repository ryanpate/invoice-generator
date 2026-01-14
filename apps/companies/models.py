"""
Company model for InvoiceKits.
"""
import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class Company(models.Model):
    """Company profile with branding settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company',
        null=True,
        blank=True,
        help_text='Legacy field - use owner instead'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_companies',
        null=True,  # Nullable initially for migration
        blank=True,
        help_text='Company owner (subscription holder)'
    )
    name = models.CharField(max_length=255)
    logo = models.ImageField(
        upload_to='logos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Recommended size: 400x200 pixels'
    )
    signature = models.ImageField(
        upload_to='signatures/%Y/%m/',
        blank=True,
        null=True,
        help_text='Digital signature image for invoices. Recommended: PNG with transparent background, 400x100 pixels'
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='United States')

    # Tax information
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='EIN, VAT number, etc.'
    )

    # Default invoice settings
    default_currency = models.CharField(
        max_length=3,
        choices=settings.CURRENCIES,
        default='USD'
    )
    default_payment_terms = models.CharField(
        max_length=20,
        choices=settings.PAYMENT_TERMS,
        default='net_30'
    )
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Default tax rate percentage'
    )
    default_template = models.CharField(
        max_length=50,
        default='clean_slate'
    )
    default_notes = models.TextField(
        blank=True,
        help_text='Default notes/payment instructions to include on invoices'
    )

    # Branding
    accent_color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text='Hex color code for invoice accent color'
    )

    # Invoice numbering
    invoice_prefix = models.CharField(
        max_length=10,
        default='INV-',
        help_text='Prefix for invoice numbers'
    )
    next_invoice_number = models.PositiveIntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name

    def get_full_address(self):
        """Return formatted full address."""
        parts = [
            self.address_line1,
            self.address_line2,
            f"{self.city}, {self.state} {self.postal_code}".strip(),
            self.country
        ]
        return '\n'.join(part for part in parts if part and part.strip())

    def get_next_invoice_number(self):
        """Generate the next invoice number and increment counter."""
        number = f"{self.invoice_prefix}{self.next_invoice_number:05d}"
        self.next_invoice_number += 1
        self.save(update_fields=['next_invoice_number'])
        return number

    def save(self, *args, **kwargs):
        # Delete old logo/signature when updating with new ones
        if self.pk:
            try:
                old_company = Company.objects.get(pk=self.pk)
                if old_company.logo and old_company.logo != self.logo:
                    old_company.logo.delete(save=False)
                if old_company.signature and old_company.signature != self.signature:
                    old_company.signature.delete(save=False)
            except Company.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def get_effective_owner(self):
        """Get the company owner (supports legacy user field)."""
        return self.owner or self.user

    def get_team_member_count(self):
        """Return count of team members (excluding owner)."""
        return self.team_members.count()

    def get_pending_invitation_count(self):
        """Return count of pending (non-expired) invitations."""
        return self.pending_invitations.filter(
            accepted=False,
            expires_at__gt=timezone.now()
        ).count()

    def get_total_seat_usage(self):
        """Return total seats used (members + pending invitations)."""
        return self.get_team_member_count() + self.get_pending_invitation_count()

    def can_add_team_member(self):
        """Check if company can add more team members."""
        owner = self.get_effective_owner()
        if not owner:
            return False
        limit = owner.get_team_seat_limit()
        if limit == 0:
            return False
        if limit == -1:  # Unlimited
            return True
        return self.get_total_seat_usage() < limit

    def is_admin(self, user):
        """Check if user is an admin (owner or has admin role)."""
        if user == self.get_effective_owner():
            return True
        membership = self.team_members.filter(user=user).first()
        return membership and membership.role == 'admin'

    def is_member(self, user):
        """Check if user belongs to this company (owner or team member)."""
        if user == self.get_effective_owner():
            return True
        return self.team_members.filter(user=user).exists()


class TeamMember(models.Model):
    """Team member associated with a company."""

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='team_members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations_sent'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'user']
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"


class TeamInvitation(models.Model):
    """Pending invitation to join a company team."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='pending_invitations'
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=TeamMember.ROLE_CHOICES,
        default='member'
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_invitations_sent'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Team Invitation'
        verbose_name_plural = 'Team Invitations'

    def __str__(self):
        return f"Invitation: {self.email} to {self.company.name}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the invitation has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if invitation is still valid (not accepted and not expired)."""
        return not self.accepted and not self.is_expired
