"""
Service for converting time entries into invoices.
"""
from decimal import Decimal
from django.utils import timezone
from ..models import Invoice, LineItem, TimeEntry


def create_invoice_from_time_entries(entries, company, user, grouping='detailed', template_style='clean_slate'):
    """
    Create an invoice from a queryset of time entries.

    Args:
        entries: QuerySet of TimeEntry objects to bill
        company: Company object for the invoice
        user: User creating the invoice
        grouping: 'detailed' (one line per entry) or 'summary' (grouped by description)
        template_style: Invoice template style slug

    Returns:
        Invoice object if successful, None otherwise
    """
    if not entries.exists():
        return None

    # Get first entry's client info for the invoice
    first_entry = entries.first()
    client_name = first_entry.client_name or 'Client'
    client_email = first_entry.client_email or ''

    # Check if all entries have the same client
    unique_clients = entries.values_list('client_email', flat=True).distinct()
    if unique_clients.count() > 1:
        # Multiple clients - use generic name
        client_name = 'Multiple Clients'
        client_email = ''

    # Generate invoice number
    today = timezone.now()
    prefix = today.strftime('%Y%m')
    count = Invoice.objects.filter(
        company=company,
        invoice_number__startswith=f'INV-{prefix}'
    ).count() + 1
    invoice_number = f'INV-{prefix}-{count:04d}'

    # Calculate date range for invoice name
    dates = list(entries.values_list('date', flat=True).distinct())
    if len(dates) == 1:
        date_range = dates[0].strftime('%B %d, %Y')
    else:
        min_date = min(dates)
        max_date = max(dates)
        if min_date.month == max_date.month:
            date_range = f"{min_date.strftime('%B %d')}-{max_date.strftime('%d, %Y')}"
        else:
            date_range = f"{min_date.strftime('%B %d')} - {max_date.strftime('%B %d, %Y')}"

    invoice_name = f"Time Billing - {date_range}"

    # Create the invoice
    invoice = Invoice.objects.create(
        company=company,
        invoice_number=invoice_number,
        invoice_name=invoice_name,
        status='draft',
        client_name=client_name,
        client_email=client_email,
        invoice_date=today.date(),
        payment_terms=company.default_payment_terms,
        currency=company.default_currency,
        tax_rate=company.default_tax_rate,
        template_style=template_style,
        notes=company.default_notes,
    )

    # Create line items based on grouping mode
    if grouping == 'detailed':
        # One line item per time entry
        for i, entry in enumerate(entries.order_by('date', 'created_at')):
            hours = entry.duration_hours
            LineItem.objects.create(
                invoice=invoice,
                description=f"{entry.description} ({entry.date.strftime('%m/%d/%y')})",
                quantity=hours,
                rate=entry.hourly_rate,
                order=i
            )
    else:
        # Summary mode - group by description and rate
        from collections import defaultdict
        grouped = defaultdict(lambda: {'total_seconds': 0, 'rate': Decimal('0')})

        for entry in entries:
            key = (entry.description, entry.hourly_rate)
            grouped[key]['total_seconds'] += entry.duration
            grouped[key]['rate'] = entry.hourly_rate

        for i, ((description, rate), data) in enumerate(grouped.items()):
            hours = Decimal(str(data['total_seconds'])) / Decimal('3600')
            LineItem.objects.create(
                invoice=invoice,
                description=description,
                quantity=hours,
                rate=rate,
                order=i
            )

    # Mark entries as invoiced
    entries.update(status='invoiced', invoice=invoice)

    return invoice


def get_unbilled_time_summary(company):
    """
    Get summary of unbilled time entries for a company.

    Args:
        company: Company object

    Returns:
        dict with summary stats
    """
    entries = TimeEntry.objects.filter(
        company=company,
        status='unbilled',
        billable=True
    )

    total_seconds = sum(e.duration for e in entries)
    total_value = sum(e.billable_amount for e in entries)
    hours = Decimal(str(total_seconds)) / Decimal('3600')

    # Group by client
    from collections import defaultdict
    by_client = defaultdict(lambda: {'hours': Decimal('0'), 'value': Decimal('0'), 'entries': 0})

    for entry in entries:
        client_key = entry.client_email or 'No Client'
        by_client[client_key]['hours'] += entry.duration_hours
        by_client[client_key]['value'] += entry.billable_amount
        by_client[client_key]['entries'] += 1

    return {
        'total_entries': entries.count(),
        'total_hours': hours,
        'total_value': total_value,
        'by_client': dict(by_client),
    }
