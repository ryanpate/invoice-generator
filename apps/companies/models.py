"""
Company model for InvoiceKits.
"""
from django.db import models
from django.conf import settings


class Company(models.Model):
    """Company profile with branding settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company'
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
