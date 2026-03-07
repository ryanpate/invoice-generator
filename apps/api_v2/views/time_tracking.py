"""
Time tracking views for API v2.

Endpoints
---------
TimeEntryV2ViewSet (router-registered at /api/v2/time/entries/)
  list            GET    /api/v2/time/entries/              list user's entries
  create          POST   /api/v2/time/entries/              manual entry (hours + minutes)
  retrieve        GET    /api/v2/time/entries/{id}/         single entry
  update          PUT    /api/v2/time/entries/{id}/         full update
  partial_update  PATCH  /api/v2/time/entries/{id}/         partial update
  destroy         DELETE /api/v2/time/entries/{id}/         delete

Function views (registered in urls_time.py)
  timer_start     POST   /api/v2/time/timer/start/          start new timer
  timer_stop      POST   /api/v2/time/timer/{id}/stop/      stop timer -> TimeEntry
  timer_discard   POST   /api/v2/time/timer/{id}/discard/   discard timer
  timer_status    GET    /api/v2/time/timer/status/         all active timers
  bill_time       POST   /api/v2/time/bill/                 convert entries to invoice
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.invoices.models import ActiveTimer, TimeEntry
from apps.invoices.services.time_billing import create_invoice_from_time_entries
from apps.api_v2.serializers.time_tracking import (
    ActiveTimerV2Serializer,
    TimeEntryCreateV2Serializer,
    TimeEntryV2Serializer,
)


# ---------------------------------------------------------------------------
# TimeEntry ViewSet
# ---------------------------------------------------------------------------

class TimeEntryV2ViewSet(viewsets.ModelViewSet):
    """
    CRUD for time entries scoped to the authenticated user.

    Query parameters
    ----------------
    ?status=  filter by status (unbilled | invoiced | paid)
    ?search=  filter by description or client name/email (case-insensitive)
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return TimeEntryV2Serializer
        return TimeEntryCreateV2Serializer

    def get_queryset(self):
        user = self.request.user
        qs = TimeEntry.objects.filter(user=user).select_related('invoice').order_by(
            '-date', '-created_at'
        )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        search_param = self.request.query_params.get('search')
        if search_param:
            qs = qs.filter(
                Q(description__icontains=search_param)
                | Q(client_name__icontains=search_param)
                | Q(client_email__icontains=search_param)
            )

        return qs

    def create(self, request, *args, **kwargs):
        """Create a manual time entry and return the full read representation."""
        write_serializer = TimeEntryCreateV2Serializer(
            data=request.data, context={'request': request}
        )
        write_serializer.is_valid(raise_exception=True)
        entry = write_serializer.save()
        read_serializer = TimeEntryV2Serializer(entry, context={'request': request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update a time entry and return the full read representation."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.status != 'unbilled':
            raise PermissionDenied(
                'Only unbilled time entries can be edited.'
            )

        write_serializer = TimeEntryCreateV2Serializer(
            instance, data=request.data, partial=partial, context={'request': request}
        )
        write_serializer.is_valid(raise_exception=True)
        entry = write_serializer.save()
        read_serializer = TimeEntryV2Serializer(entry, context={'request': request})
        return Response(read_serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Timer function views
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_start(request):
    """
    Start a new timer.

    Request body (all optional)
    ---------------------------
    description  str   — what you are working on
    client_name  str
    client_email str
    hourly_rate  str   — decimal; defaults to company default or 0

    Returns 201 with ActiveTimerV2Serializer data on success.
    Returns 403 when the user's tier timer limit is reached.
    """
    user = request.user

    if not user.can_start_timer():
        max_timers = user.get_max_active_timers()
        raise PermissionDenied(
            f'Your plan allows a maximum of {max_timers} active '
            f'timer{"s" if max_timers != 1 else ""} at a time. '
            'Stop an existing timer before starting a new one.'
        )

    company = user.get_company()
    if company is None:
        raise ValidationError(
            {'detail': 'No company found for this user. Create a company profile first.'}
        )

    # Resolve hourly_rate: caller > company default > 0
    hourly_rate_raw = request.data.get('hourly_rate')
    if hourly_rate_raw is not None:
        try:
            hourly_rate = float(hourly_rate_raw)
        except (TypeError, ValueError):
            raise ValidationError({'hourly_rate': 'Must be a valid number.'})
    else:
        try:
            settings_obj = company.time_tracking_settings
            hourly_rate = float(settings_obj.default_hourly_rate)
        except Exception:
            hourly_rate = 0.0

    timer = ActiveTimer.objects.create(
        user=user,
        company=company,
        description=request.data.get('description', ''),
        client_name=request.data.get('client_name', ''),
        client_email=request.data.get('client_email', ''),
        hourly_rate=hourly_rate,
    )

    serializer = ActiveTimerV2Serializer(timer, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_stop(request, timer_id):
    """
    Stop a running timer and convert it to a TimeEntry.

    Returns 200 with TimeEntryV2Serializer data for the new entry.
    Returns 404 if the timer does not belong to the authenticated user.
    """
    timer = get_object_or_404(ActiveTimer, pk=timer_id, user=request.user)
    entry = timer.stop()
    serializer = TimeEntryV2Serializer(entry, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_discard(request, timer_id):
    """
    Discard a running timer without saving any time entry.

    Returns 204 No Content on success.
    Returns 404 if the timer does not belong to the authenticated user.
    """
    timer = get_object_or_404(ActiveTimer, pk=timer_id, user=request.user)
    timer.discard()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def timer_status(request):
    """
    Return all active timers for the authenticated user.

    Response body
    -------------
    {
        "count": <int>,
        "timers": [ <ActiveTimerV2Serializer>, ... ]
    }
    """
    timers = ActiveTimer.objects.filter(user=request.user).order_by('-started_at')
    serializer = ActiveTimerV2Serializer(timers, many=True, context={'request': request})
    return Response(
        {'count': timers.count(), 'timers': serializer.data},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Bill time — convert entries to an invoice
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bill_time(request):
    """
    Convert unbilled time entries into a draft invoice.

    Request body
    ------------
    entry_ids  list[int]  required — IDs of TimeEntry objects to bill
    grouping   str        optional — "detailed" (default) or "summary"

    Returns 201 with the new invoice's basic info on success.
    Returns 400 if entry_ids is missing/empty or entries cannot be billed.
    """
    entry_ids = request.data.get('entry_ids')
    if not entry_ids or not isinstance(entry_ids, list):
        raise ValidationError({'entry_ids': 'A non-empty list of time entry IDs is required.'})

    grouping = request.data.get('grouping', 'detailed')
    if grouping not in ('detailed', 'summary'):
        raise ValidationError({'grouping': 'Must be "detailed" or "summary".'})

    user = request.user
    company = user.get_company()
    if company is None:
        raise ValidationError(
            {'detail': 'No company found for this user. Create a company profile first.'}
        )

    # Scope to entries owned by this user that are still unbilled
    entries = TimeEntry.objects.filter(
        pk__in=entry_ids,
        user=user,
        status='unbilled',
    )

    if not entries.exists():
        raise ValidationError(
            {'entry_ids': 'No unbilled time entries found for the provided IDs.'}
        )

    # Enforce invoice creation limits before proceeding
    if not user.can_create_invoice():
        raise PermissionDenied(
            'Invoice limit reached for your current plan. '
            'Please upgrade to create more invoices.'
        )

    # Capture the count before the service marks entries as invoiced,
    # because the queryset filter (status='unbilled') would return 0 afterwards.
    entries_count = entries.count()

    invoice = create_invoice_from_time_entries(
        entries=entries,
        company=company,
        user=user,
        grouping=grouping,
    )

    if invoice is None:
        raise ValidationError({'detail': 'Failed to create invoice from time entries.'})

    # Track invoice usage
    user.increment_invoice_count()

    return Response(
        {
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'invoice_name': invoice.invoice_name,
            'client_name': invoice.client_name,
            'total': str(invoice.total),
            'status': invoice.status,
            'entries_billed': entries_count,
        },
        status=status.HTTP_201_CREATED,
    )
