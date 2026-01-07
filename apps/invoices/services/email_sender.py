"""
Invoice email sending service.
"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .pdf_generator import InvoicePDFGenerator


class InvoiceEmailService:
    """Service for sending invoices via email with PDF attachment."""

    def __init__(self, invoice):
        self.invoice = invoice
        self.company = invoice.company

    def get_default_subject(self) -> str:
        """Generate default email subject."""
        return f"Invoice {self.invoice.invoice_number} from {self.company.name}"

    def get_default_message(self) -> str:
        """Generate default email message."""
        currency_symbol = self.invoice.get_currency_symbol()
        return (
            f"Dear {self.invoice.client_name},\n\n"
            f"Please find attached invoice {self.invoice.invoice_number} "
            f"for {currency_symbol}{self.invoice.total:.2f}.\n\n"
            f"Due Date: {self.invoice.due_date.strftime('%B %d, %Y')}\n\n"
            f"If you have any questions about this invoice, please don't hesitate to contact us.\n\n"
            f"Best regards,\n"
            f"{self.company.name}"
        )

    def send(self, to_email: str, subject: str, message: str, cc_emails: list = None) -> dict:
        """
        Send invoice email with PDF attachment.

        Args:
            to_email: Primary recipient email
            subject: Email subject
            message: Email body text
            cc_emails: Optional list of CC recipient emails

        Returns:
            dict with 'success' boolean and 'error' message if failed
        """
        try:
            # Generate PDF
            pdf_generator = InvoicePDFGenerator(self.invoice)
            pdf_bytes = pdf_generator.generate()

            # Render HTML email
            html_content = render_to_string('emails/invoice_notification.html', {
                'invoice': self.invoice,
                'company': self.company,
                'message': message,
                'site_url': getattr(settings, 'SITE_URL', 'https://www.invoicekits.com'),
            })

            # Create plain text fallback
            plain_text = strip_tags(html_content)

            # Create email with attachment
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
                cc=cc_emails or [],
            )

            # Set HTML content type
            email.content_subtype = 'html'

            # Attach PDF
            pdf_filename = f"{self.invoice.invoice_number}.pdf"
            email.attach(pdf_filename, pdf_bytes, 'application/pdf')

            # Send email
            email.send(fail_silently=False)

            # Mark invoice as sent
            self.invoice.mark_as_sent()

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}
