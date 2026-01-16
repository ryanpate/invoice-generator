"""
Celery tasks for recurring invoice processing, payment reminders, and late fees.
"""
import logging
from datetime import timedelta
from decimal import Decimal
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


@shared_task(bind=True, max_retries=3)
def process_late_fees(self):
    """
    Process late fees for overdue invoices.
    Runs daily at 7:00 AM UTC via Celery Beat (1 hour after recurring invoices).
    """
    from apps.invoices.models import Invoice, LateFeeLog
    from apps.companies.models import Company

    today = timezone.now().date()
    logger.info(f"Processing late fees for {today}")

    applied_count = 0
    skipped_count = 0
    failed_count = 0

    # Get all companies with late fees enabled
    companies = Company.objects.filter(
        late_fees_enabled=True,
        late_fee_amount__gt=0
    )

    for company in companies:
        # Calculate the cutoff date (due_date + grace_days)
        grace_days = company.late_fee_grace_days or 0
        cutoff_date = today - timedelta(days=grace_days)

        # Get overdue invoices for this company that haven't had late fees applied
        overdue_invoices = Invoice.objects.filter(
            company=company,
            status__in=['sent', 'overdue'],
            due_date__lt=cutoff_date,
            late_fee_applied=0,
            late_fees_paused=False
        )

        for invoice in overdue_invoices:
            try:
                # Calculate the late fee
                fee_amount = calculate_late_fee(
                    invoice_total=invoice.total,
                    fee_type=company.late_fee_type,
                    fee_amount=company.late_fee_amount,
                    max_amount=company.late_fee_max_amount
                )

                if fee_amount <= 0:
                    skipped_count += 1
                    continue

                # Store values for logging
                total_before = invoice.total
                days_overdue = (today - invoice.due_date).days

                # Apply the late fee
                if invoice.apply_late_fee(fee_amount):
                    # Create audit log
                    LateFeeLog.objects.create(
                        invoice=invoice,
                        fee_type=company.late_fee_type,
                        fee_amount=fee_amount,
                        days_overdue=days_overdue,
                        invoice_total_before=total_before,
                        invoice_total_after=invoice.total,
                        applied_by='system'
                    )

                    applied_count += 1
                    logger.info(
                        f"Applied ${fee_amount} late fee to invoice "
                        f"{invoice.invoice_number} ({days_overdue} days overdue)"
                    )

                    # Send notification email
                    send_late_fee_notification.delay(invoice.id, float(fee_amount))
                else:
                    skipped_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Failed to apply late fee to invoice {invoice.id}: {str(e)}",
                    exc_info=True
                )

    logger.info(
        f"Late fee processing complete: "
        f"{applied_count} applied, {skipped_count} skipped, {failed_count} failed"
    )

    return {
        'applied': applied_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'date': str(today)
    }


def calculate_late_fee(invoice_total, fee_type, fee_amount, max_amount=None):
    """
    Calculate the late fee amount based on type and settings.

    Args:
        invoice_total: The invoice total amount
        fee_type: 'flat' or 'percentage'
        fee_amount: The fee amount or percentage
        max_amount: Optional maximum cap

    Returns:
        Decimal: The calculated late fee
    """
    if fee_type == 'flat':
        calculated_fee = Decimal(str(fee_amount))
    elif fee_type == 'percentage':
        calculated_fee = (Decimal(str(invoice_total)) * Decimal(str(fee_amount)) / 100)
    else:
        calculated_fee = Decimal('0')

    # Apply max cap if set
    if max_amount and calculated_fee > Decimal(str(max_amount)):
        calculated_fee = Decimal(str(max_amount))

    return calculated_fee.quantize(Decimal('0.01'))


@shared_task(bind=True, max_retries=3)
def send_late_fee_notification(self, invoice_id, fee_amount):
    """
    Send email notification when a late fee is applied.
    """
    from apps.invoices.models import Invoice

    try:
        invoice = Invoice.objects.select_related(
            'company', 'company__owner'
        ).get(id=invoice_id)

        # Send to business owner
        owner = invoice.company.owner
        if owner and owner.email:
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
                f"You can view and manage this invoice in your dashboard.\n\n"
                f"Best regards,\n"
                f"The InvoiceKits Team"
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

        # Optionally notify client
        if invoice.client_email:
            send_late_fee_client_notification.delay(invoice_id, fee_amount)

    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found for late fee notification")
    except Exception as e:
        logger.error(
            f"Failed to send late fee notification: {str(e)}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60 * 5)


@shared_task(bind=True, max_retries=3)
def send_late_fee_client_notification(self, invoice_id, fee_amount):
    """
    Send email notification to client when a late fee is applied.
    """
    from apps.invoices.models import Invoice

    try:
        invoice = Invoice.objects.select_related('company').get(id=invoice_id)

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
            f"The invoice was originally due on {invoice.due_date.strftime('%B %d, %Y')}.\n\n"
            f"Please submit payment at your earliest convenience to avoid additional fees.\n\n"
            f"If you have any questions, please contact us.\n\n"
            f"Best regards,\n"
            f"{invoice.company.name}"
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

    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found for client notification")
    except Exception as e:
        logger.error(
            f"Failed to send late fee client notification: {str(e)}",
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60 * 5)
