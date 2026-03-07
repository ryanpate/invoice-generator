"""
Invoice views for API v2.
"""
from django.db.models import Q
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.invoices.models import Invoice, LineItem, RecurringInvoice, RecurringLineItem
from apps.invoices.services.email_sender import InvoiceEmailService
from apps.invoices.services.pdf_generator import InvoicePDFGenerator
from apps.api_v2.serializers.invoices import (
    InvoiceCreateV2Serializer,
    InvoiceDetailV2Serializer,
    InvoiceListV2Serializer,
)


class InvoiceV2ViewSet(viewsets.ModelViewSet):
    """
    Invoice CRUD endpoints for the iOS app.

    list:   GET  /api/v2/invoices/            — paginated list, supports ?status= and ?search=
    create: POST /api/v2/invoices/            — create invoice with nested line_items
    retrieve: GET  /api/v2/invoices/{id}/     — full detail with line items
    update: PUT  /api/v2/invoices/{id}/       — full update
    partial_update: PATCH /api/v2/invoices/{id}/ — partial update
    destroy: DELETE /api/v2/invoices/{id}/   — delete invoice

    Custom actions:
      pdf              GET  /api/v2/invoices/{id}/pdf/
      send             POST /api/v2/invoices/{id}/send/
      mark_paid        POST /api/v2/invoices/{id}/mark-paid/
      mark_sent        POST /api/v2/invoices/{id}/mark-sent/
      toggle_reminders POST /api/v2/invoices/{id}/toggle-reminders/
      toggle_late_fees POST /api/v2/invoices/{id}/toggle-late-fees/
      make_recurring   POST /api/v2/invoices/{id}/make-recurring/
    """

    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------
    # Serializer dispatch
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListV2Serializer
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceCreateV2Serializer
        return InvoiceDetailV2Serializer

    # ------------------------------------------------------------------
    # Queryset — scoped to the authenticated user's company
    # ------------------------------------------------------------------

    def get_queryset(self):
        user = self.request.user
        qs = (
            Invoice.objects.filter(company__user=user)
            .prefetch_related('line_items')
            .order_by('-created_at')
        )

        # Optional ?status= filter (e.g. draft, sent, paid, overdue, cancelled)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # Optional ?search= filter across invoice number, name, and client name/email
        search_param = self.request.query_params.get('search')
        if search_param:
            qs = qs.filter(
                Q(invoice_number__icontains=search_param)
                | Q(invoice_name__icontains=search_param)
                | Q(client_name__icontains=search_param)
                | Q(client_email__icontains=search_param)
            )

        return qs

    # ------------------------------------------------------------------
    # Create — enforce billing tier limits, return full detail on success
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        if not self.request.user.can_create_invoice():
            raise PermissionDenied(
                'Invoice limit reached for your current plan. '
                'Please upgrade to create more invoices.'
            )
        serializer.save()

    def create(self, request, *args, **kwargs):
        """Override to return detail serializer (with id) after creation."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        invoice = write_serializer.instance
        read_serializer = InvoiceDetailV2Serializer(
            invoice, context={'request': request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate and stream the invoice PDF."""
        invoice = self.get_object()
        generator = InvoicePDFGenerator(invoice)
        pdf_bytes = generator.generate()

        response = FileResponse(
            iter([pdf_bytes]),
            content_type='application/pdf',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{invoice.invoice_number}.pdf"'
        )
        return response

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send invoice to client via email with PDF attachment.

        Optional request body fields:
          - to_email   (str)  — override recipient; defaults to invoice.client_email
          - subject    (str)  — override email subject
          - message    (str)  — override email body
          - cc_emails  (list) — additional CC addresses
        """
        invoice = self.get_object()

        if not invoice.client_email and not request.data.get('to_email'):
            raise ValidationError(
                {'to_email': 'No client email on invoice. Provide to_email in request body.'}
            )

        service = InvoiceEmailService(invoice)
        to_email = request.data.get('to_email') or invoice.client_email
        subject = request.data.get('subject') or service.get_default_subject()
        message = request.data.get('message') or service.get_default_message()
        cc_emails = request.data.get('cc_emails', [])

        result = service.send(
            to_email=to_email,
            subject=subject,
            message=message,
            cc_emails=cc_emails,
        )

        if result['success']:
            serializer = InvoiceDetailV2Serializer(
                invoice, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {'error': result.get('error', 'Failed to send invoice.')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        """Mark an invoice as paid."""
        invoice = self.get_object()
        invoice.mark_as_paid()
        serializer = InvoiceDetailV2Serializer(invoice, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-sent')
    def mark_sent(self, request, pk=None):
        """Mark an invoice as sent (without emailing)."""
        invoice = self.get_object()
        invoice.mark_as_sent()
        serializer = InvoiceDetailV2Serializer(invoice, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-reminders')
    def toggle_reminders(self, request, pk=None):
        """Toggle automated payment reminders on/off for this invoice."""
        invoice = self.get_object()
        invoice.reminders_paused = not invoice.reminders_paused
        invoice.save(update_fields=['reminders_paused', 'updated_at'])
        return Response(
            {
                'reminders_paused': invoice.reminders_paused,
                'invoice_id': invoice.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='toggle-late-fees')
    def toggle_late_fees(self, request, pk=None):
        """Toggle automatic late fees on/off for this invoice."""
        invoice = self.get_object()
        invoice.late_fees_paused = not invoice.late_fees_paused
        invoice.save(update_fields=['late_fees_paused', 'updated_at'])
        return Response(
            {
                'late_fees_paused': invoice.late_fees_paused,
                'invoice_id': invoice.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='make-recurring')
    def make_recurring(self, request, pk=None):
        """
        Convert an existing invoice into a recurring invoice template.

        Optional request body fields:
          - name       (str) — internal name; defaults to invoice name or client name
          - frequency  (str) — weekly/biweekly/monthly/quarterly/yearly; defaults to monthly
          - start_date (str) — YYYY-MM-DD; defaults to today
        """
        from django.utils import timezone

        user = request.user
        # Professional+ required for recurring invoices
        if not user.has_recurring_invoices():
            raise PermissionDenied(
                'Recurring invoices require a Professional or Business subscription.'
            )

        invoice = self.get_object()

        name = (
            request.data.get('name')
            or invoice.invoice_name
            or f"Recurring — {invoice.client_name}"
        )
        frequency = request.data.get('frequency', 'monthly')
        start_date_raw = request.data.get('start_date')

        valid_frequencies = ['weekly', 'biweekly', 'monthly', 'quarterly', 'yearly']
        if frequency not in valid_frequencies:
            raise ValidationError(
                {'frequency': f'Must be one of: {", ".join(valid_frequencies)}.'}
            )

        if start_date_raw:
            from datetime import date
            try:
                start_date = date.fromisoformat(start_date_raw)
            except ValueError:
                raise ValidationError(
                    {'start_date': 'Invalid date format. Use YYYY-MM-DD.'}
                )
        else:
            start_date = timezone.now().date()

        recurring = RecurringInvoice.objects.create(
            company=invoice.company,
            name=name,
            client_name=invoice.client_name,
            client_email=invoice.client_email,
            client_phone=invoice.client_phone,
            client_address=invoice.client_address,
            frequency=frequency,
            start_date=start_date,
            next_run_date=start_date,
            currency=invoice.currency,
            payment_terms=invoice.payment_terms,
            tax_rate=invoice.tax_rate,
            template_style=invoice.template_style,
            notes=invoice.notes,
        )

        # Copy line items from the source invoice
        for item in invoice.line_items.all():
            RecurringLineItem.objects.create(
                recurring_invoice=recurring,
                description=item.description,
                quantity=item.quantity,
                rate=item.rate,
                order=item.order,
            )

        return Response(
            {
                'recurring_invoice_id': recurring.id,
                'name': recurring.name,
                'frequency': recurring.frequency,
                'start_date': recurring.start_date.isoformat(),
                'next_run_date': recurring.next_run_date.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
