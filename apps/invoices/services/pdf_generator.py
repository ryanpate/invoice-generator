"""
PDF generation service using WeasyPrint.
"""
import os
from io import BytesIO
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.base import ContentFile
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


class InvoicePDFGenerator:
    """Generate PDF invoices using WeasyPrint with HTML templates."""

    TEMPLATE_STYLES = {
        'clean_slate': {
            'primary_color': '#1F2937',
            'accent_color': '#3B82F6',
            'background': '#FFFFFF',
            'text_color': '#1F2937',
            'font_family': 'Inter, sans-serif',
            'header_style': 'minimal',
        },
        'executive': {
            'primary_color': '#1E3A5F',
            'accent_color': '#C9A227',
            'background': '#FAFAFA',
            'text_color': '#1E3A5F',
            'font_family': 'Georgia, serif',
            'header_style': 'classic',
        },
        'bold_modern': {
            'primary_color': '#7C3AED',
            'accent_color': '#EC4899',
            'background': '#FFFFFF',
            'text_color': '#111827',
            'font_family': 'Poppins, sans-serif',
            'header_style': 'bold',
        },
        'classic_professional': {
            'primary_color': '#374151',
            'accent_color': '#059669',
            'background': '#FFFFFF',
            'text_color': '#374151',
            'font_family': 'Times New Roman, serif',
            'header_style': 'traditional',
        },
        'neon_edge': {
            'primary_color': '#0F172A',
            'accent_color': '#22D3EE',
            'background': '#0F172A',
            'text_color': '#E2E8F0',
            'font_family': 'Roboto Mono, monospace',
            'header_style': 'dark',
        },
    }

    def __init__(self, invoice):
        self.invoice = invoice
        self.company = invoice.company
        self.style_config = self.TEMPLATE_STYLES.get(
            invoice.template_style,
            self.TEMPLATE_STYLES['clean_slate']
        )

    def get_context(self):
        """Build context for PDF template."""
        # Use company's accent color if set
        accent_color = self.company.accent_color or self.style_config['accent_color']

        return {
            'invoice': self.invoice,
            'company': self.company,
            'line_items': self.invoice.line_items.all(),
            'style': {
                **self.style_config,
                'accent_color': accent_color,
            },
            'show_watermark': self.company.user.shows_watermark(),
            'currency_symbol': self.invoice.get_currency_symbol(),
        }

    def generate(self):
        """Generate PDF and return as bytes."""
        template_name = f'invoices/pdf/{self.invoice.template_style}.html'

        # Fallback to clean_slate if template doesn't exist
        try:
            html_content = render_to_string(template_name, self.get_context())
        except Exception:
            html_content = render_to_string(
                'invoices/pdf/clean_slate.html',
                self.get_context()
            )

        # Configure fonts
        font_config = FontConfiguration()

        # Generate PDF
        html = HTML(string=html_content, base_url=settings.BASE_DIR)
        pdf_bytes = html.write_pdf(font_config=font_config)

        return pdf_bytes

    def save_to_invoice(self):
        """Generate PDF and save to invoice model."""
        pdf_bytes = self.generate()

        filename = f"{self.invoice.invoice_number}.pdf"
        self.invoice.pdf_file.save(
            filename,
            ContentFile(pdf_bytes),
            save=True
        )

        return self.invoice.pdf_file

    @classmethod
    def generate_preview(cls, invoice_data, company):
        """Generate a preview PDF from invoice data without saving."""
        # Create a temporary invoice-like object for preview
        class PreviewInvoice:
            def __init__(self, data, company):
                self.invoice_number = data.get('invoice_number', 'PREVIEW-001')
                self.client_name = data.get('client_name', 'Preview Client')
                self.client_email = data.get('client_email', '')
                self.client_phone = data.get('client_phone', '')
                self.client_address = data.get('client_address', '')
                self.invoice_date = data.get('invoice_date')
                self.due_date = data.get('due_date')
                self.payment_terms = data.get('payment_terms', 'net_30')
                self.currency = data.get('currency', 'USD')
                self.subtotal = data.get('subtotal', 0)
                self.tax_rate = data.get('tax_rate', 0)
                self.tax_amount = data.get('tax_amount', 0)
                self.total = data.get('total', 0)
                self.notes = data.get('notes', '')
                self.template_style = data.get('template_style', 'clean_slate')
                self.company = company

            def get_currency_symbol(self):
                symbols = {
                    'USD': '$', 'EUR': '€', 'GBP': '£',
                    'CAD': 'C$', 'AUD': 'A$', 'JPY': '¥', 'INR': '₹'
                }
                return symbols.get(self.currency, self.currency)

        class PreviewLineItem:
            def __init__(self, data):
                self.description = data.get('description', '')
                self.quantity = data.get('quantity', 1)
                self.rate = data.get('rate', 0)
                self.amount = data.get('amount', 0)

        preview_invoice = PreviewInvoice(invoice_data, company)

        # Create line items
        class LineItemManager:
            def __init__(self, items):
                self._items = [PreviewLineItem(item) for item in items]

            def all(self):
                return self._items

        preview_invoice.line_items = LineItemManager(
            invoice_data.get('line_items', [])
        )

        generator = cls(preview_invoice)
        return generator.generate()
