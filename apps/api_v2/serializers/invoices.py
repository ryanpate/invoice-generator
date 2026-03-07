"""
Invoice serializers for API v2.
"""
from rest_framework import serializers

from apps.companies.models import Company
from apps.invoices.models import Invoice, LineItem, RecurringInvoice, RecurringLineItem


class LineItemV2Serializer(serializers.ModelSerializer):
    """Serializer for invoice line items."""

    class Meta:
        model = LineItem
        fields = ['id', 'description', 'quantity', 'rate', 'amount', 'order']
        read_only_fields = ['id', 'amount']


class InvoiceListV2Serializer(serializers.ModelSerializer):
    """Serializer for the invoice list endpoint — lightweight, no line items."""

    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'invoice_name',
            'client_name',
            'client_email',
            'status',
            'total',
            'currency',
            'currency_symbol',
            'due_date',
            'created_at',
            'reminders_paused',
            'late_fees_paused',
            'late_fee_applied',
        ]


class InvoiceDetailV2Serializer(serializers.ModelSerializer):
    """Serializer for the invoice detail endpoint — full data including line items."""

    line_items = LineItemV2Serializer(many=True, read_only=True)
    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'invoice_name',
            'client_name',
            'client_email',
            'client_phone',
            'client_address',
            'status',
            'total',
            'currency',
            'currency_symbol',
            'due_date',
            'created_at',
            'reminders_paused',
            'late_fees_paused',
            'late_fee_applied',
            # Detail-only fields below
            'invoice_date',
            'payment_terms',
            'subtotal',
            'tax_rate',
            'tax_amount',
            'discount_amount',
            'notes',
            'template_style',
            'line_items',
            'late_fee_applied_at',
            'original_total',
            'paid_at',
            'sent_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'invoice_number',
            'subtotal',
            'tax_amount',
            'total',
            'created_at',
            'updated_at',
        ]


class InvoiceCreateV2Serializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating invoices.

    Accepts nested line_items. Validates that the user has access to the
    requested template_style. On create, auto-generates the invoice number
    and calculates totals. On update, replaces all line items and
    recalculates.
    """

    line_items = LineItemV2Serializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'invoice_name',
            'client_name',
            'client_email',
            'client_phone',
            'client_address',
            'invoice_date',
            'payment_terms',
            'currency',
            'tax_rate',
            'discount_amount',
            'notes',
            'template_style',
            'line_items',
        ]

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one line item is required.')
        return value

    def validate_template_style(self, value):
        user = self.context['request'].user
        available_templates = user.get_available_templates()
        if value not in available_templates:
            raise serializers.ValidationError(
                f'Template "{value}" is not available on your plan.'
            )
        return value

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')
        user = self.context['request'].user

        # Get or create company for this user
        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"},
        )

        # Create the invoice (no due_date yet — calculated below)
        invoice = Invoice.objects.create(
            company=company,
            invoice_number=company.get_next_invoice_number(),
            **validated_data,
        )

        # Create line items — use the client-supplied order when present,
        # otherwise fall back to the iteration index.
        for idx, item_data in enumerate(line_items_data):
            item_data.setdefault('order', idx)
            LineItem.objects.create(invoice=invoice, **item_data)

        # Calculate due date based on payment terms and recalculate totals
        invoice.due_date = invoice.calculate_due_date()
        invoice.calculate_totals()
        invoice.save()

        # Track invoice usage for billing tier enforcement
        user.increment_invoice_count()

        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        # Update scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if line_items_data is not None:
            # Replace all existing line items
            instance.line_items.all().delete()
            for idx, item_data in enumerate(line_items_data):
                item_data.setdefault('order', idx)
                LineItem.objects.create(invoice=instance, **item_data)

        # Recalculate due date and totals after any update
        instance.due_date = instance.calculate_due_date()
        instance.calculate_totals()
        instance.save()

        return instance
