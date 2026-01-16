"""
Payment reminder email sending service.
"""
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from .pdf_generator import InvoicePDFGenerator

logger = logging.getLogger(__name__)


class PaymentReminderService:
    """Service for sending automated payment reminder emails."""

    REMINDER_TEMPLATES = {
        'before': 'emails/payment_reminder_before.html',
        'due': 'emails/payment_reminder_due.html',
        'overdue': 'emails/payment_reminder_overdue.html',
    }

    REMINDER_SUBJECTS = {
        'before': 'Reminder: Invoice {invoice_number} Due Soon',
        'due': 'Payment Due Today: Invoice {invoice_number}',
        'overdue': 'OVERDUE: Invoice {invoice_number} - Immediate Attention Required',
    }

    def __init__(self, invoice):
        self.invoice = invoice
        self.company = invoice.company

    def get_reminder_type(self, days_offset):
        """Determine reminder type based on days offset."""
        if days_offset < 0:
            return 'before'
        elif days_offset == 0:
            return 'due'
        else:
            return 'overdue'

    def get_subject(self, reminder_type):
        """Generate email subject based on reminder type."""
        template = self.REMINDER_SUBJECTS.get(reminder_type, self.REMINDER_SUBJECTS['before'])
        return template.format(invoice_number=self.invoice.invoice_number)

    def get_days_label(self, days_offset):
        """Get human-readable label for days offset."""
        if days_offset == 0:
            return 'today'
        elif days_offset == -1:
            return 'in 1 day'
        elif days_offset < 0:
            return f'in {abs(days_offset)} days'
        elif days_offset == 1:
            return '1 day ago'
        else:
            return f'{days_offset} days ago'

    def get_custom_message(self, reminder_type, reminder_settings):
        """Get custom message from settings if available."""
        if reminder_settings:
            if reminder_type == 'before' and reminder_settings.custom_message_before:
                return reminder_settings.custom_message_before
            elif reminder_type == 'due' and reminder_settings.custom_message_due:
                return reminder_settings.custom_message_due
            elif reminder_type == 'overdue' and reminder_settings.custom_message_overdue:
                return reminder_settings.custom_message_overdue
        return None

    def send_reminder(self, days_offset, reminder_settings=None) -> dict:
        """
        Send a payment reminder email.

        Args:
            days_offset: Days relative to due date (-3 = 3 days before, 0 = on due, 7 = 7 days after)
            reminder_settings: PaymentReminderSettings instance for custom messages

        Returns:
            dict with 'success' boolean, 'reminder_type', and 'error' message if failed
        """
        from apps.invoices.models import PaymentReminderLog

        # Validate invoice state
        if self.invoice.status in ['paid', 'cancelled', 'draft']:
            return {
                'success': False,
                'error': f'Invoice status is {self.invoice.status}, no reminder needed'
            }

        if not self.invoice.client_email:
            return {
                'success': False,
                'error': 'No client email address available'
            }

        if self.invoice.reminders_paused:
            return {
                'success': False,
                'error': 'Reminders paused for this invoice'
            }

        # Check if already sent
        if PaymentReminderLog.objects.filter(
            invoice=self.invoice,
            days_offset=days_offset,
            success=True
        ).exists():
            return {
                'success': False,
                'error': f'Reminder for {days_offset:+d} days already sent'
            }

        reminder_type = self.get_reminder_type(days_offset)
        custom_message = self.get_custom_message(reminder_type, reminder_settings)

        try:
            # Generate PDF
            pdf_generator = InvoicePDFGenerator(self.invoice)
            pdf_bytes = pdf_generator.generate()

            # Prepare template context
            context = {
                'invoice': self.invoice,
                'company': self.company,
                'reminder_type': reminder_type,
                'days_offset': days_offset,
                'days_label': self.get_days_label(days_offset),
                'custom_message': custom_message,
                'site_url': getattr(settings, 'SITE_URL', 'https://www.invoicekits.com'),
                'public_invoice_url': self.invoice.get_public_url(),
            }

            # Render HTML email
            template = self.REMINDER_TEMPLATES.get(reminder_type, self.REMINDER_TEMPLATES['before'])
            html_content = render_to_string(template, context)

            # Prepare recipients
            recipients = [self.invoice.client_email]
            cc_emails = []

            # Add business owner CC if enabled
            if reminder_settings and reminder_settings.cc_business_owner:
                owner = self.company.get_effective_owner()
                if owner and owner.email:
                    cc_emails.append(owner.email)

            # Create email
            subject = self.get_subject(reminder_type)
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
                cc=cc_emails,
            )
            email.content_subtype = 'html'

            # Attach PDF
            pdf_filename = f"{self.invoice.invoice_number}.pdf"
            email.attach(pdf_filename, pdf_bytes, 'application/pdf')

            # Send email
            email.send(fail_silently=False)

            # Log successful send
            PaymentReminderLog.objects.create(
                invoice=self.invoice,
                days_offset=days_offset,
                reminder_type=reminder_type,
                recipient_email=self.invoice.client_email,
                success=True
            )

            logger.info(
                f"Sent {reminder_type} reminder for invoice {self.invoice.invoice_number} "
                f"({days_offset:+d} days) to {self.invoice.client_email}"
            )

            return {
                'success': True,
                'reminder_type': reminder_type,
                'recipient': self.invoice.client_email
            }

        except Exception as e:
            # Log failed send
            PaymentReminderLog.objects.create(
                invoice=self.invoice,
                days_offset=days_offset,
                reminder_type=reminder_type,
                recipient_email=self.invoice.client_email,
                success=False,
                error_message=str(e)
            )

            logger.error(
                f"Failed to send reminder for invoice {self.invoice.invoice_number}: {str(e)}",
                exc_info=True
            )

            return {
                'success': False,
                'reminder_type': reminder_type,
                'error': str(e)
            }

    @classmethod
    def get_invoices_needing_reminders(cls, days_offset):
        """
        Get all invoices that need a reminder for the given days offset.

        Args:
            days_offset: Days relative to due date

        Returns:
            QuerySet of Invoice objects needing reminders
        """
        from apps.invoices.models import Invoice, PaymentReminderLog, PaymentReminderSettings

        today = timezone.now().date()
        target_due_date = today - timezone.timedelta(days=days_offset)

        # Get invoices with matching due date that are sent or overdue
        invoices = Invoice.objects.filter(
            due_date=target_due_date,
            status__in=['sent', 'overdue'],
            reminders_paused=False,
            client_email__isnull=False
        ).exclude(
            client_email=''
        ).select_related('company', 'company__owner')

        # Exclude invoices that already have a reminder sent for this offset
        already_sent = PaymentReminderLog.objects.filter(
            days_offset=days_offset,
            success=True
        ).values_list('invoice_id', flat=True)

        invoices = invoices.exclude(pk__in=already_sent)

        # Filter to only companies with reminders enabled and this day enabled
        result_invoices = []
        for invoice in invoices:
            try:
                settings = invoice.company.reminder_settings
                if settings.reminders_enabled and days_offset in settings.get_enabled_days():
                    result_invoices.append(invoice)
            except PaymentReminderSettings.DoesNotExist:
                # No reminder settings, skip this invoice
                continue

        return result_invoices
