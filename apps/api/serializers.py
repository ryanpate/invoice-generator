"""
API Serializers for Invoice Generator Pro.
"""
from rest_framework import serializers
from apps.invoices.models import Invoice, LineItem
from apps.companies.models import Company


class LineItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items."""

    class Meta:
        model = LineItem
        fields = ['id', 'description', 'quantity', 'rate', 'amount', 'order']
        read_only_fields = ['id', 'amount']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for invoice list view."""
    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'client_name', 'client_email',
            'status', 'total', 'currency', 'currency_symbol',
            'due_date', 'created_at'
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for invoice detail view."""
    line_items = LineItemSerializer(many=True, read_only=True)
    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'status',
            'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_date', 'due_date', 'payment_terms',
            'currency', 'currency_symbol',
            'subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total',
            'notes', 'template_style',
            'line_items', 'pdf_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'subtotal', 'tax_amount', 'total', 'created_at', 'updated_at']

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
        return None


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating invoices."""
    line_items = LineItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_date', 'payment_terms', 'currency',
            'tax_rate', 'discount_amount', 'notes', 'template_style',
            'line_items'
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

        # Get or create company
        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"}
        )

        # Create invoice
        invoice = Invoice.objects.create(
            company=company,
            invoice_number=company.get_next_invoice_number(),
            **validated_data
        )

        # Create line items
        for idx, item_data in enumerate(line_items_data):
            LineItem.objects.create(invoice=invoice, order=idx, **item_data)

        # Calculate totals and due date
        invoice.due_date = invoice.calculate_due_date()
        invoice.calculate_totals()
        invoice.save()

        # Increment user's invoice count
        user.increment_invoice_count()

        return invoice


class BatchInvoiceSerializer(serializers.Serializer):
    """Serializer for batch invoice creation from CSV data."""
    client_name = serializers.CharField(max_length=255)
    client_email = serializers.EmailField(required=False, allow_blank=True)
    client_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    client_address = serializers.CharField(required=False, allow_blank=True)
    item_description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    rate = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    currency = serializers.CharField(max_length=3, required=False, default='USD')
    payment_terms = serializers.CharField(max_length=20, required=False, default='net_30')
    notes = serializers.CharField(required=False, allow_blank=True)


class TemplateSerializer(serializers.Serializer):
    """Serializer for invoice templates."""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    best_for = serializers.CharField()
    premium = serializers.BooleanField()
    available = serializers.BooleanField()
