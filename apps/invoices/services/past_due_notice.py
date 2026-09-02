"""
Past-due notice: the document a business sends when an invoice has gone unpaid.

The late-fee calculators are the highest-intent pages on the site, but they
only ever offered to help the visitor create a *new* invoice. This turns the
number they just computed into the thing they actually want -- a notice that
asks for the money, with the state's rules cited underneath it.

Deliberately not an Invoice: nothing here is saved, there is no line-item
model, and it never touches the invoice numbering sequence. It is a
standalone document built from a form.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.template.loader import render_to_string
from django.utils.text import slugify
from xhtml2pdf import pisa

CURRENCY_SYMBOLS = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'CAD': 'C$',
    'AUD': 'A$', 'JPY': '¥', 'INR': '₹',
}


def build_notice_context(data, today=None):
    """Turn cleaned form data into everything the notice template needs.

    Separated from rendering so the arithmetic -- which is a demand for
    money and therefore has to be right -- can be tested on its own.
    """
    from apps.invoices.views import STATE_LATE_FEE_DATA

    today = today or date.today()
    original = Decimal(data['original_amount'])
    fee = Decimal(data['late_fee'])
    due_date = data['due_date']

    state_info = STATE_LATE_FEE_DATA.get((data.get('state') or '').lower()) or None

    symbol = CURRENCY_SYMBOLS.get(data.get('currency', 'USD'), '')
    total = original + fee

    def money(value):
        """$2,508.00 -- floatformat alone gives $2508.00, which reads as sloppy
        on a document that is asking someone for that exact sum."""
        return f'{symbol}{value:,.2f}'

    return {
        'business_name': data['business_name'],
        'business_email': data.get('business_email', ''),
        'client_name': data['client_name'],
        'invoice_number': data.get('invoice_number', ''),
        'original_amount': original,
        'late_fee': fee,
        'total_due': total,
        'original_amount_display': money(original),
        'late_fee_display': money(fee),
        'total_due_display': money(total),
        'due_date': due_date,
        'issue_date': today,
        'days_overdue': max(0, (today - due_date).days),
        'currency': data.get('currency', 'USD'),
        'currency_symbol': CURRENCY_SYMBOLS.get(data.get('currency', 'USD'), ''),
        'state_info': state_info,
        'notes': data.get('notes', ''),
    }


def render_notice_pdf(context):
    """Render the notice to PDF bytes via the same xhtml2pdf path as invoices."""
    html = render_to_string('invoices/pdf/past_due_notice.html', context)
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result)
    if pdf.err:
        raise RuntimeError(f'Past-due notice PDF generation failed: {pdf.err}')
    return result.getvalue()


def notice_filename(client_name):
    """Safe, readable filename. slugify also guarantees no quote or ; in the header."""
    slug = slugify(client_name)[:60]
    return f'past-due-notice-{slug}.pdf' if slug else 'past-due-notice.pdf'
