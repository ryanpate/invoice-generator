"""
Recurring invoice serializers for API v2.
"""
from rest_framework import serializers

from apps.invoices.models import RecurringInvoice, RecurringLineItem


class RecurringLineItemV2Serializer(serializers.ModelSerializer):
    """Serializer for recurring invoice line items."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RecurringLineItem
        fields = ['id', 'description', 'quantity', 'rate', 'amount', 'order']
        read_only_fields = ['id', 'amount']


class RecurringInvoiceListV2Serializer(serializers.ModelSerializer):
    """Lightweight serializer for the recurring invoice list — no line items."""

    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RecurringInvoice
        fields = [
            'id',
            'name',
            'client_name',
            'client_email',
            'frequency',
            'frequency_display',
            'status',
            'status_display',
            'next_run_date',
            'invoices_generated',
            'created_at',
        ]


class RecurringInvoiceDetailV2Serializer(serializers.ModelSerializer):
    """Full detail serializer for a single recurring invoice, including line items."""

    line_items = RecurringLineItemV2Serializer(many=True, read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RecurringInvoice
        fields = [
            'id',
            'name',
            'client_name',
            'client_email',
            'client_phone',
            'client_address',
            'frequency',
            'frequency_display',
            'status',
            'status_display',
            'start_date',
            'end_date',
            'next_run_date',
            'currency',
            'payment_terms',
            'tax_rate',
            'template_style',
            'notes',
            'send_email_on_generation',
            'auto_send_to_client',
            'invoices_generated',
            'last_generated_at',
            'line_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'invoices_generated',
            'last_generated_at',
            'created_at',
            'updated_at',
        ]


class RecurringInvoiceCreateV2Serializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating recurring invoices with nested line items.

    On create, auto-associates the company of the authenticated user.
    On update, replaces all line items if provided.
    """

    line_items = RecurringLineItemV2Serializer(many=True)

    class Meta:
        model = RecurringInvoice
        fields = [
            'name',
            'client_name',
            'client_email',
            'client_phone',
            'client_address',
            'frequency',
            'start_date',
            'end_date',
            'currency',
            'payment_terms',
            'tax_rate',
            'template_style',
            'notes',
            'send_email_on_generation',
            'auto_send_to_client',
            'line_items',
        ]

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one line item is required.')
        return value

    def create(self, validated_data):
        from apps.companies.models import Company

        line_items_data = validated_data.pop('line_items')
        user = self.context['request'].user

        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"},
        )

        # start_date drives next_run_date on creation
        start_date = validated_data.get('start_date')
        recurring = RecurringInvoice.objects.create(
            company=company,
            next_run_date=start_date,
            **validated_data,
        )

        for idx, item_data in enumerate(line_items_data):
            item_data.setdefault('order', idx)
            RecurringLineItem.objects.create(recurring_invoice=recurring, **item_data)

        return recurring

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for idx, item_data in enumerate(line_items_data):
                item_data.setdefault('order', idx)
                RecurringLineItem.objects.create(recurring_invoice=instance, **item_data)

        return instance
