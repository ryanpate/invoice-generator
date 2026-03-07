"""
Recurring invoice views for API v2.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.invoices.models import RecurringInvoice
from apps.api_v2.serializers.recurring import (
    RecurringInvoiceListV2Serializer,
    RecurringInvoiceDetailV2Serializer,
    RecurringInvoiceCreateV2Serializer,
)


class RecurringInvoiceV2ViewSet(viewsets.ModelViewSet):
    """
    Recurring invoice CRUD endpoints for the iOS app.

    Requires Professional or Business subscription.

    list:    GET  /api/v2/recurring/
    create:  POST /api/v2/recurring/
    retrieve: GET  /api/v2/recurring/{id}/
    update:  PUT  /api/v2/recurring/{id}/
    partial_update: PATCH /api/v2/recurring/{id}/
    destroy: DELETE /api/v2/recurring/{id}/

    Custom actions:
      toggle_status  POST /api/v2/recurring/{id}/toggle-status/
      generate_now   POST /api/v2/recurring/{id}/generate-now/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = None

    # ------------------------------------------------------------------
    # Permission guard — all actions require the recurring invoices feature
    # ------------------------------------------------------------------

    def _require_recurring_permission(self):
        if not self.request.user.has_recurring_invoices():
            raise PermissionDenied(
                'Recurring invoices require a Professional or Business subscription.'
            )

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._require_recurring_permission()

    # ------------------------------------------------------------------
    # Serializer dispatch
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == 'list':
            return RecurringInvoiceListV2Serializer
        if self.action in ('create', 'update', 'partial_update'):
            return RecurringInvoiceCreateV2Serializer
        return RecurringInvoiceDetailV2Serializer

    # ------------------------------------------------------------------
    # Queryset — scoped to the authenticated user's company
    # ------------------------------------------------------------------

    def get_queryset(self):
        user = self.request.user
        return (
            RecurringInvoice.objects.filter(company__user=user)
            .prefetch_related('line_items')
            .order_by('-created_at')
        )

    # ------------------------------------------------------------------
    # Create — enforce recurring invoice limits, return detail on success
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        if not self.request.user.can_create_recurring_invoice():
            raise PermissionDenied(
                'You have reached the recurring invoice limit for your plan. '
                'Please upgrade to create more.'
            )
        serializer.save()

    def create(self, request, *args, **kwargs):
        """Override to return detail serializer after creation."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        recurring = write_serializer.instance
        read_serializer = RecurringInvoiceDetailV2Serializer(
            recurring, context={'request': request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """
        Toggle a recurring invoice between active and paused.

        If currently active → pause.
        If currently paused → resume.
        Cancelled recurring invoices cannot be toggled.
        """
        recurring = self.get_object()

        if recurring.status == 'cancelled':
            return Response(
                {'error': 'Cannot toggle a cancelled recurring invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if recurring.status == 'active':
            recurring.pause()
        else:
            recurring.resume()

        serializer = RecurringInvoiceDetailV2Serializer(
            recurring, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='generate-now')
    def generate_now(self, request, pk=None):
        """
        Manually trigger invoice generation from this recurring template.

        The generated Invoice is returned as a summary dict.
        """
        recurring = self.get_object()

        if recurring.status == 'cancelled':
            return Response(
                {'error': 'Cannot generate from a cancelled recurring invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice = recurring.generate_invoice()

        return Response(
            {
                'generated_invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'client_name': invoice.client_name,
                'total': str(invoice.total),
                'currency': invoice.currency,
                'status': invoice.status,
                'recurring_invoice_id': recurring.id,
                'invoices_generated': recurring.invoices_generated,
                'next_run_date': recurring.next_run_date.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
