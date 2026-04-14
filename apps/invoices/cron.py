"""
Synchronous daily task runners.

Replaces Celery workers/beat with plain Python functions invoked from a
management command on a Railway cron schedule. Each run_* function returns
a summary dict and catches exceptions at the per-item level so one bad
record does not abort the whole batch.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers (synchronous replacements for former Celery tasks)
# ---------------------------------------------------------------------------

def _send_recurring_invoice_notification(recurring, invoice):
    try:
        user = recurring.company.owner
        subject = f"Recurring Invoice Generated: {invoice.invoice_number}"
        html_message = render_to_string('emails/recurring_invoice_generated.html', {
            'user': user,
            'recurring': recurring,
            'invoice': invoice,
            'site_url': getattr(settings, 'SITE_URL', ''),
        })
        plain_message = (
            f"Hi {user.first_name or user.email},\n\n"
            f"Your recurring invoice '{recurring.name}' has generated a new invoice.\n\n"
            f"Invoice Number: {invoice.invoice_number}\n"
            f"Client: {invoice.client_name}\n"
            f"Amount: {invoice.get_currency_symbol()}{invoice.total}\n\n"
            f"Log in to view and manage your invoices.\n\n"
            f"Best regards,\nThe InvoiceKits Team"
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent recurring invoice notification to {user.email}")
    except Exception as e:
        logger.error(f"Failed recurring notification: {e}", exc_info=True)


def _send_invoice_to_client(invoice):
    from apps.invoices.services.pdf_generator import generate_invoice_pdf

    try:
        if not invoice.client_email:
            logger.warning(f"Cannot send invoice {invoice.id} - no client email")
            return

        if not invoice.pdf_file:
            user = invoice.company.owner
            generate_invoice_pdf(invoice, show_watermark=user.shows_watermark())

        subject = f"Invoice {invoice.invoice_number} from {invoice.company.name}"
        html_message = render_to_string('emails/invoice_to_client.html', {
            'invoice': invoice,
            'company': invoice.company,
        })
        plain_message = (
            f"Dear {invoice.client_name},\n\n"
            f"Please find attached invoice {invoice.invoice_number}.\n\n"
            f"Amount Due: {invoice.get_currency_symbol()}{invoice.total}\n"
            f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}\n\n"
            f"Thank you for your business.\n\n"
            f"Best regards,\n{invoice.company.name}"
        )

        email = EmailMessage(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invoice.client_email],
        )
        if invoice.pdf_file:
            email.attach_file(invoice.pdf_file.path)
        email.send(fail_silently=False)
        invoice.mark_as_sent()
        logger.info(f"Sent invoice {invoice.invoice_number} to {invoice.client_email}")
    except Exception as e:
        logger.error(f"Failed invoice-to-client send: {e}", exc_info=True)


def _calculate_late_fee(invoice_total, fee_type, fee_amount, max_amount=None):
    if fee_type == 'flat':
        calculated_fee = Decimal(str(fee_amount))
    elif fee_type == 'percentage':
        calculated_fee = (Decimal(str(invoice_total)) * Decimal(str(fee_amount)) / 100)
    else:
        calculated_fee = Decimal('0')

    if max_amount and calculated_fee > Decimal(str(max_amount)):
        calculated_fee = Decimal(str(max_amount))

    return calculated_fee.quantize(Decimal('0.01'))


def _send_late_fee_owner_notification(invoice, fee_amount):
    try:
        owner = invoice.company.owner
        if not (owner and owner.email):
            return
        subject = f"Late Fee Applied: Invoice {invoice.invoice_number}"
        html_message = render_to_string('emails/late_fee_applied.html', {
            'user': owner,
            'invoice': invoice,
            'fee_amount': fee_amount,
            'site_url': getattr(settings, 'SITE_URL', ''),
        })
        plain_message = (
            f"Hi {owner.first_name or owner.email},\n\n"
            f"A late fee of ${fee_amount:.2f} has been automatically applied to "
            f"invoice {invoice.invoice_number} for {invoice.client_name}.\n\n"
            f"Original Amount: ${invoice.original_total:.2f}\n"
            f"Late Fee: ${fee_amount:.2f}\n"
            f"New Total: ${invoice.total:.2f}\n\n"
            f"The invoice was due on {invoice.due_date.strftime('%B %d, %Y')}.\n\n"
            f"Best regards,\nThe InvoiceKits Team"
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent late fee notification to {owner.email}")
    except Exception as e:
        logger.error(f"Failed late fee owner notification: {e}", exc_info=True)


def _send_late_fee_client_notification(invoice, fee_amount):
    try:
        if not invoice.client_email:
            return
        subject = f"Late Fee Notice: Invoice {invoice.invoice_number}"
        html_message = render_to_string('emails/late_fee_client_notice.html', {
            'invoice': invoice,
            'company': invoice.company,
            'fee_amount': fee_amount,
        })
        plain_message = (
            f"Dear {invoice.client_name},\n\n"
            f"A late fee of ${fee_amount:.2f} has been applied to your overdue invoice "
            f"{invoice.invoice_number}.\n\n"
            f"Original Amount: ${invoice.original_total:.2f}\n"
            f"Late Fee: ${fee_amount:.2f}\n"
            f"New Total Due: ${invoice.total:.2f}\n\n"
            f"Please submit payment at your earliest convenience.\n\n"
            f"Best regards,\n{invoice.company.name}"
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invoice.client_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent late fee client notification to {invoice.client_email}")
    except Exception as e:
        logger.error(f"Failed late fee client notification: {e}", exc_info=True)


def _send_single_payment_reminder(invoice, days_offset, reminder_settings):
    from apps.invoices.services.reminder_sender import PaymentReminderService
    try:
        service = PaymentReminderService(invoice)
        result = service.send_reminder(days_offset, reminder_settings)
        if result.get('success'):
            logger.info(
                f"Sent {result.get('reminder_type', 'unknown')} reminder for "
                f"invoice {invoice.invoice_number}"
            )
        else:
            logger.warning(
                f"Reminder not sent for invoice {invoice.invoice_number}: "
                f"{result.get('error', 'unknown')}"
            )
        return result
    except Exception as e:
        logger.error(f"Failed payment reminder send: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Top-level runners (invoked by management command)
# ---------------------------------------------------------------------------

def run_recurring_invoices():
    from apps.invoices.models import RecurringInvoice

    today = timezone.now().date()
    logger.info(f"Processing recurring invoices for {today}")

    recurring_invoices = RecurringInvoice.objects.filter(
        status='active',
        next_run_date__lte=today,
    ).select_related('company', 'company__owner')

    processed = 0
    failed = 0
    for recurring in recurring_invoices:
        try:
            user = recurring.company.owner
            if not user.has_recurring_invoices():
                logger.warning(
                    f"Skipping recurring {recurring.id} - user lacks access"
                )
                continue

            invoice = recurring.generate_invoice()
            processed += 1
            logger.info(
                f"Generated invoice {invoice.invoice_number} from recurring "
                f"{recurring.id} ({recurring.name})"
            )

            if recurring.send_email_on_generation:
                _send_recurring_invoice_notification(recurring, invoice)

            if recurring.auto_send_to_client and recurring.client_email:
                _send_invoice_to_client(invoice)
        except Exception as e:
            failed += 1
            logger.error(
                f"Failed recurring invoice {recurring.id}: {e}", exc_info=True
            )

    summary = {'processed': processed, 'failed': failed, 'date': str(today)}
    logger.info(f"Recurring invoices complete: {summary}")
    return summary


def run_payment_reminders():
    from apps.invoices.models import PaymentReminderSettings
    from apps.invoices.services.reminder_sender import PaymentReminderService

    today = timezone.now().date()
    logger.info(f"Processing payment reminders for {today}")

    reminder_days = [-3, -1, 0, 3, 7, 14]
    sent = 0
    failed = 0
    skipped = 0

    for days_offset in reminder_days:
        invoices = PaymentReminderService.get_invoices_needing_reminders(days_offset)
        for invoice in invoices:
            try:
                try:
                    reminder_settings = invoice.company.reminder_settings
                except PaymentReminderSettings.DoesNotExist:
                    skipped += 1
                    continue

                result = _send_single_payment_reminder(
                    invoice, days_offset, reminder_settings
                )
                if result.get('success'):
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error(
                    f"Failed reminder for invoice {invoice.id}: {e}",
                    exc_info=True,
                )

    summary = {'sent': sent, 'failed': failed, 'skipped': skipped, 'date': str(today)}
    logger.info(f"Payment reminders complete: {summary}")
    return summary


def run_late_fees():
    from apps.companies.models import Company
    from apps.invoices.models import Invoice, LateFeeLog

    today = timezone.now().date()
    logger.info(f"Processing late fees for {today}")

    applied = 0
    skipped = 0
    failed = 0

    companies = Company.objects.filter(
        late_fees_enabled=True,
        late_fee_amount__gt=0,
    )

    for company in companies:
        grace_days = company.late_fee_grace_days or 0
        cutoff_date = today - timedelta(days=grace_days)

        overdue_invoices = Invoice.objects.filter(
            company=company,
            status__in=['sent', 'overdue'],
            due_date__lt=cutoff_date,
            late_fee_applied=0,
            late_fees_paused=False,
        )

        for invoice in overdue_invoices:
            try:
                fee_amount = _calculate_late_fee(
                    invoice_total=invoice.total,
                    fee_type=company.late_fee_type,
                    fee_amount=company.late_fee_amount,
                    max_amount=company.late_fee_max_amount,
                )
                if fee_amount <= 0:
                    skipped += 1
                    continue

                total_before = invoice.total
                days_overdue = (today - invoice.due_date).days

                if invoice.apply_late_fee(fee_amount):
                    LateFeeLog.objects.create(
                        invoice=invoice,
                        fee_type=company.late_fee_type,
                        fee_amount=fee_amount,
                        days_overdue=days_overdue,
                        invoice_total_before=total_before,
                        invoice_total_after=invoice.total,
                        applied_by='system',
                    )
                    applied += 1
                    logger.info(
                        f"Applied ${fee_amount} late fee to invoice "
                        f"{invoice.invoice_number} ({days_overdue} days overdue)"
                    )
                    _send_late_fee_owner_notification(invoice, float(fee_amount))
                    _send_late_fee_client_notification(invoice, float(fee_amount))
                else:
                    skipped += 1
            except Exception as e:
                failed += 1
                logger.error(
                    f"Failed late fee for invoice {invoice.id}: {e}",
                    exc_info=True,
                )

    summary = {
        'applied': applied,
        'skipped': skipped,
        'failed': failed,
        'date': str(today),
    }
    logger.info(f"Late fees complete: {summary}")
    return summary


def run_nurture_emails():
    from apps.accounts.models import CustomUser

    now = timezone.now()
    sent = 0
    failed = 0

    site_url = getattr(settings, 'SITE_URL', 'https://www.invoicekits.com')

    # Day 2 emails
    day2_start = now - timedelta(days=3)
    day2_end = now - timedelta(days=2)
    day2_users = CustomUser.objects.filter(
        nurture_email_step=0,
        created_at__gte=day2_start,
        created_at__lt=day2_end,
        is_active=True,
    )
    for user in day2_users:
        try:
            html_message = render_to_string('emails/nurture_day2.html', {
                'user': user,
                'site_url': site_url,
            })
            send_mail(
                subject='Create your first invoice in 60 seconds',
                message=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            user.nurture_email_step = 1
            user.save(update_fields=['nurture_email_step'])
            sent += 1
            logger.info(f"Sent Day 2 nurture email to {user.email}")
        except Exception as e:
            failed += 1
            logger.error(f"Failed Day 2 nurture for {user.email}: {e}", exc_info=True)

    # Day 5 emails
    day5_start = now - timedelta(days=6)
    day5_end = now - timedelta(days=5)
    day5_users = CustomUser.objects.filter(
        nurture_email_step=1,
        created_at__gte=day5_start,
        created_at__lt=day5_end,
        is_active=True,
    )
    for user in day5_users:
        try:
            html_message = render_to_string('emails/nurture_day5.html', {
                'user': user,
                'site_url': site_url,
            })
            send_mail(
                subject='3 features that help you get paid faster',
                message=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            user.nurture_email_step = 2
            user.save(update_fields=['nurture_email_step'])
            sent += 1
            logger.info(f"Sent Day 5 nurture email to {user.email}")
        except Exception as e:
            failed += 1
            logger.error(f"Failed Day 5 nurture for {user.email}: {e}", exc_info=True)

    summary = {'sent': sent, 'failed': failed}
    logger.info(f"Nurture emails complete: {summary}")
    return summary


def run_all():
    """Run every daily task in order, catching top-level failures per task."""
    results = {}
    for name, fn in (
        ('recurring_invoices', run_recurring_invoices),
        ('payment_reminders', run_payment_reminders),
        ('late_fees', run_late_fees),
        ('nurture_emails', run_nurture_emails),
    ):
        try:
            results[name] = fn()
        except Exception as e:
            logger.error(f"Top-level failure in {name}: {e}", exc_info=True)
            results[name] = {'error': str(e)}
    return results
