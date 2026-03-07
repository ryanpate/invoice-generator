"""
Company serializers for API v2.
"""
from rest_framework import serializers

from apps.companies.models import Company


class CompanyV2Serializer(serializers.ModelSerializer):
    """
    Full company profile serializer.

    logo and signature are returned as absolute URLs when present.
    On update, use multipart/form-data to send image files.
    """

    logo_url = serializers.SerializerMethodField()
    signature_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'website',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'tax_id',
            'default_currency',
            'default_payment_terms',
            'default_tax_rate',
            'default_template',
            'default_notes',
            'accent_color',
            'invoice_prefix',
            'next_invoice_number',
            # Read-only image URLs (use dedicated upload endpoints to set images)
            'logo_url',
            'signature_url',
            # Late fee settings
            'late_fees_enabled',
            'late_fee_type',
            'late_fee_amount',
            'late_fee_grace_days',
            'late_fee_max_amount',
            # Stripe Connect (read-only status)
            'stripe_connect_onboarding_complete',
            'stripe_connect_charges_enabled',
            'stripe_connect_payouts_enabled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'next_invoice_number',
            'stripe_connect_onboarding_complete',
            'stripe_connect_charges_enabled',
            'stripe_connect_payouts_enabled',
            'logo_url',
            'signature_url',
            'created_at',
            'updated_at',
        ]

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_signature_url(self, obj):
        request = self.context.get('request')
        if obj.signature and request:
            return request.build_absolute_uri(obj.signature.url)
        return None
