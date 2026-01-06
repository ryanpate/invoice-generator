"""
API Views for Invoice Generator Pro.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.http import FileResponse

from apps.invoices.models import Invoice, LineItem
from apps.invoices.services.pdf_generator import InvoicePDFGenerator
from .serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    TemplateSerializer,
)
from .authentication import APIKeyAuthentication


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for invoice management.

    list: Get all invoices
    retrieve: Get a single invoice
    create: Create a new invoice
    update: Update an invoice
    destroy: Delete an invoice
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer

    def get_queryset(self):
        return Invoice.objects.filter(
            company__user=self.request.user
        ).prefetch_related('line_items').order_by('-created_at')

    def perform_create(self, serializer):
        # Check if user can create more invoices
        if not self.request.user.can_create_invoice():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Invoice limit reached for your plan.')

        serializer.save()

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate and return PDF for an invoice."""
        invoice = self.get_object()

        generator = InvoicePDFGenerator(invoice)
        pdf_bytes = generator.generate()

        response = FileResponse(
            iter([pdf_bytes]),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
        return response

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark invoice as sent."""
        invoice = self.get_object()
        invoice.mark_as_sent()
        return Response({'status': 'sent'})

    @action(detail=True, methods=['post'])
    def paid(self, request, pk=None):
        """Mark invoice as paid."""
        invoice = self.get_object()
        invoice.mark_as_paid()
        return Response({'status': 'paid'})


class TemplateListView(APIView):
    """List available invoice templates."""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        available_templates = user.get_available_templates()

        templates = []
        for key, value in settings.INVOICE_TEMPLATES.items():
            templates.append({
                'id': key,
                'name': value['name'],
                'description': value['description'],
                'best_for': value['best_for'],
                'premium': value.get('premium', False),
                'available': key in available_templates,
            })

        serializer = TemplateSerializer(templates, many=True)
        return Response(serializer.data)


class UsageView(APIView):
    """Get current API usage statistics."""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        tier_config = settings.SUBSCRIPTION_TIERS.get(user.subscription_tier, {})

        return Response({
            'subscription_tier': user.subscription_tier,
            'invoices': {
                'used': user.invoices_created_this_month,
                'limit': tier_config.get('invoices_per_month', 5),
                'unlimited': tier_config.get('invoices_per_month') == -1,
            },
            'api_calls': {
                'used': user.api_calls_this_month,
                'limit': tier_config.get('api_calls_per_month', 0),
                'unlimited': tier_config.get('api_calls_per_month') == -1,
            },
            'features': {
                'batch_upload': tier_config.get('batch_upload', False),
                'api_access': tier_config.get('api_access', False),
                'watermark': tier_config.get('watermark', True),
            },
            'reset_date': user.usage_reset_date.isoformat(),
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_info(request):
    """API information and version."""
    return Response({
        'name': 'Invoice Generator Pro API',
        'version': '1.0.0',
        'documentation': request.build_absolute_uri('/api/docs/'),
        'endpoints': {
            'invoices': request.build_absolute_uri('/api/v1/invoices/'),
            'templates': request.build_absolute_uri('/api/v1/templates/'),
            'usage': request.build_absolute_uri('/api/v1/usage/'),
        },
        'authentication': 'Include X-API-Key header with your API key',
    })
