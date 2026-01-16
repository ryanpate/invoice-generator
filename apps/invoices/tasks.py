"""
Celery tasks for recurring invoice processing.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_recurring_invoices(self):
    """
    Process all recurring invoices that are due today.
    Runs daily at 6 AM UTC via Celery Beat.
    """
    from apps.invoices.models import RecurringInvoice

    today = timezone.now().date()
    logger.info(f"Processing recurring invoices for {today}")

    # Get all active recurring invoices that should run today
    recurring_invoices = RecurringInvoice.objects.filter(
        status='active',
        next_run_date__lte=today
    ).select_related('company', 'company__owner')

    processed_count = 0
    failed_count = 0

    for recurring in recurring_invoices:
        try:
            # Check if user still has recurring invoice access
            user = recurring.company.owner
            if not user.has_recurring_invoices():
                logger.warning(
                    f"Skipping recurring invoice {recurring.id} - "
                    f"user {user.email} no longer has recurring access"
                )
                continue

            # Generate the invoice
            invoice = recurring.generate_invoice()
            processed_count += 1

            logger.info(
                f"Generated invoice {invoice.invoice_number} from "
                f"recurring invoice {recurring.id} ({recurring.name})"
            )

            # Send notification to owner if enabled
            if recurring.send_email_on_generation:
                send_recurring_invoice_notification.delay(
                    recurring.id,
                    invoice.id
                )

            # Auto-send to client if enabled
            if recurring.auto_send_to_client and recurring.client_email:
                send_invoice_to_client.delay(invoice.id)

        except Exception as e:
            failed_count += 1
            logger.error(
                f"Failed to process recurring invoice {recurring.id}: {str(e)}",
                exc_info=True
            )

    logger.info(
        f"Recurring invoice processing complete: "
        f"{processed_count} processed, {failed_count} failed"
    )

    return {
        'processed': processed_count,
        'failed': failed_count,
        'date': str(today)
    }


@shared_task(bind=True, max_retries=3)
def send_recurring_invoice_notification(self, recurring_invoice_id, invoice_id):
    """
    Send email notification to user when a recurring invoice is generated.
    """
    from apps.invoices.models import RecurringInvoice, Invoice

    try:
        recurring = RecurringInvoice.objects.select_related(
            'company__owner'
        ).get(id=recurring_invoice_id)
        invoice = Invoice.objects.get(id=invoice_id)
        user = recurring.company.owner

        subject = f"Recurring Invoice Generated: {invoice.invoice_number}"

        # Render HTML email
        html_message = render_to_string('emails/recurring_invoice_generated.html', {
            'user': user,
            'recurring': recurring,
            'invoice': invoice,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else '',
        })

        # Plain text fallback
        plain_message = (
            f"Hi {user.first_name or user.email},\n\n"
            f"Your recurring invoice '{recurring.name}' has generated a new invoice.\n\n"
            f"Invoice Number: {invoice.invoice_number}\n"
            f"Client: {invoice.client_name}\n"
            f"Amount: {invoice.get_currency_symbol()}{invoice.total}\n\n"
            f"Log in to view and manage your invoices.\n\n"
            f"Best regards,\n"
            f"The InvoiceKits Team"
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
        logger.error(
            f"Failed to send recurring invoice notification: {str(e)}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=3)
def send_invoice_to_client(self, invoice_id):
    """
    Send invoice directly to client email.
    """
    from apps.invoices.models import Invoice
    from apps.invoices.services.pdf_generator import generate_invoice_pdf

    try:
        invoice = Invoice.objects.select_related('company__owner').get(id=invoice_id)

        if not invoice.client_email:
            logger.warning(f"Cannot send invoice {invoice_id} - no client email")
            return

        # Generate PDF if not already generated
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
            f"Best regards,\n"
            f"{invoice.company.name}"
        )

        from django.core.mail import EmailMessage

        email = EmailMessage(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invoice.client_email],
        )

        # Attach PDF if available
        if invoice.pdf_file:
            email.attach_file(invoice.pdf_file.path)

        email.send(fail_silently=False)

        # Mark invoice as sent
        invoice.mark_as_sent()

        logger.info(f"Sent invoice {invoice.invoice_number} to {invoice.client_email}")

    except Exception as e:
        logger.error(
            f"Failed to send invoice to client: {str(e)}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes


@shared_task
def generate_recurring_invoice_now(recurring_invoice_id):
    """
    Manually trigger generation of a recurring invoice.
    Called when user clicks "Generate Now" button.
    """
    from apps.invoices.models import RecurringInvoice

    try:
        recurring = RecurringInvoice.objects.select_related(
            'company__owner'
        ).get(id=recurring_invoice_id)

        # Check access
        user = recurring.company.owner
        if not user.has_recurring_invoices():
            logger.warning(
                f"Cannot generate - user {user.email} doesn't have recurring access"
            )
            return {'success': False, 'error': 'No recurring invoice access'}

        # Generate invoice
        invoice = recurring.generate_invoice()

        logger.info(
            f"Manually generated invoice {invoice.invoice_number} from "
            f"recurring invoice {recurring.id}"
        )

        # Send notifications if enabled
        if recurring.send_email_on_generation:
            send_recurring_invoice_notification.delay(recurring.id, invoice.id)

        if recurring.auto_send_to_client and recurring.client_email:
            send_invoice_to_client.delay(invoice.id)

        return {
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number
        }

    except RecurringInvoice.DoesNotExist:
        logger.error(f"Recurring invoice {recurring_invoice_id} not found")
        return {'success': False, 'error': 'Recurring invoice not found'}
    except Exception as e:
        logger.error(f"Failed to generate recurring invoice: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def process_payment_reminders(self):
    """
    Process all payment reminders that are due today.
    Runs daily at 6:30 AM UTC via Celery Beat (30 mins after recurring invoices).
    """
    from apps.invoices.models import PaymentReminderSettings
    from apps.invoices.services.reminder_sender import PaymentReminderService

    today = timezone.now().date()
    logger.info(f"Processing payment reminders for {today}")

    # All possible reminder days (relative to due date)
    reminder_days = [-3, -1, 0, 3, 7, 14]

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for days_offset in reminder_days:
        invoices = PaymentReminderService.get_invoices_needing_reminders(days_offset)

        for invoice in invoices:
            try:
                # Get reminder settings for this company
                try:
                    reminder_settings = invoice.company.reminder_settings
                except PaymentReminderSettings.DoesNotExist:
                    skipped_count += 1
                    continue

                # Queue the individual reminder task
                send_payment_reminder.delay(invoice.id, days_offset, reminder_settings.id)
                sent_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Failed to queue reminder for invoice {invoice.id}: {str(e)}",
                    exc_info=True
                )

    logger.info(
        f"Payment reminder processing complete: "
        f"{sent_count} queued, {failed_count} failed, {skipped_count} skipped"
    )

    return {
        'queued': sent_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'date': str(today)
    }


@shared_task(bind=True, max_retries=3)
def send_payment_reminder(self, invoice_id, days_offset, reminder_settings_id=None):
    """
    Send an individual payment reminder email.
    """
    from apps.invoices.models import Invoice, PaymentReminderSettings
    from apps.invoices.services.reminder_sender import PaymentReminderService

    try:
        invoice = Invoice.objects.select_related(
            'company', 'company__owner'
        ).get(id=invoice_id)

        reminder_settings = None
        if reminder_settings_id:
            try:
                reminder_settings = PaymentReminderSettings.objects.get(id=reminder_settings_id)
            except PaymentReminderSettings.DoesNotExist:
                pass

        # Send the reminder
        service = PaymentReminderService(invoice)
        result = service.send_reminder(days_offset, reminder_settings)

        if result['success']:
            logger.info(
                f"Sent {result.get('reminder_type', 'unknown')} reminder for "
                f"invoice {invoice.invoice_number} to {result.get('recipient')}"
            )
        else:
            logger.warning(
                f"Reminder not sent for invoice {invoice.invoice_number}: "
                f"{result.get('error', 'Unknown error')}"
            )

        return result

    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found for reminder")
        return {'success': False, 'error': 'Invoice not found'}

    except Exception as e:
        logger.error(
            f"Failed to send payment reminder for invoice {invoice_id}: {str(e)}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes
