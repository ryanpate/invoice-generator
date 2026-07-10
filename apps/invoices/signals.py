"""
Invoice signals for automated email notifications.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from allauth.account.signals import user_signed_up

from .models import Invoice
from .services.email_sender import InvoiceEmailService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Invoice)
def send_payment_receipt_on_paid(sender, instance, **kwargs):
    """
    Send payment receipt email when invoice status changes to 'paid'.

    This signal checks if the status has changed from any other status to 'paid'
    and automatically sends a payment receipt to both the client and business owner.
    """
    # Check if status changed to 'paid'
    if instance.status == 'paid' and instance._original_status != 'paid':
        try:
            service = InvoiceEmailService(instance)
            result = service.send_payment_receipt()

            if result['success']:
                logger.info(
                    f"Payment receipt sent for invoice {instance.invoice_number} "
                    f"to {result.get('recipients', [])}"
                )
            else:
                logger.error(
                    f"Failed to send payment receipt for invoice {instance.invoice_number}: "
                    f"{result.get('error', 'Unknown error')}"
                )
        except Exception as e:
            logger.error(
                f"Exception sending payment receipt for invoice {instance.invoice_number}: {e}"
            )

        # Update the original status after processing
        instance._original_status = instance.status


@receiver(user_signed_up)
def redeem_try_draft_on_signup(sender, request, user, **kwargs):
    """
    Save the /try/ draft invoice to the new account.

    A visitor who built an invoice on /try/ has it stashed in their session;
    signup should keep that work, not discard it. Creates their company (named
    from the draft) and the invoice, then records the pk so the dashboard can
    land them on it. Must never break signup — any failure is logged and
    swallowed.
    """
    from datetime import date
    from decimal import Decimal

    from .views import TRY_DRAFT_SESSION_KEY, TRY_SAVED_INVOICE_SESSION_KEY

    draft = request.session.pop(TRY_DRAFT_SESSION_KEY, None)
    if not draft:
        return

    try:
        from apps.companies.models import Company
        from .models import LineItem

        company = Company.objects.create(
            user=user,
            owner=user,
            name=draft['company_name'],
            email=draft.get('company_email') or user.email or '',
        )
        invoice = Invoice.objects.create(
            company=company,
            invoice_number=company.get_next_invoice_number(),
            client_name=draft['client_name'],
            client_email=draft.get('client_email', ''),
            invoice_date=date.fromisoformat(draft['invoice_date']),
            due_date=date.fromisoformat(draft['due_date']),
            payment_terms=draft.get('payment_terms', 'net_30'),
            currency=draft.get('currency', 'USD'),
            tax_rate=Decimal(str(draft.get('tax_rate', 0))),
            notes=draft.get('notes', ''),
            template_style=draft.get('template_style', 'clean_slate'),
        )
        for order, item in enumerate(draft['line_items']):
            LineItem.objects.create(
                invoice=invoice,
                description=str(item['description'])[:500],
                quantity=Decimal(str(item['quantity'])),
                rate=Decimal(str(item['rate'])),
                order=order,
            )
        user.increment_invoice_count()
        request.session[TRY_SAVED_INVOICE_SESSION_KEY] = invoice.pk
        logger.info(
            f"Redeemed /try/ draft as invoice {invoice.invoice_number} "
            f"for new user {user.pk}"
        )
    except Exception:
        logger.exception(f"Failed to redeem /try/ draft for new user {user.pk}")
