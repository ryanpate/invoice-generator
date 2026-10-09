"""Every invoice template must render through xhtml2pdf.

Executive used CSS (linear-gradient, calc) that xhtml2pdf cannot parse, so
every Executive PDF raised a TypeError the views did not catch: a 500 on
download, and a failed send or reminder.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.test import TestCase

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice, LineItem
from apps.invoices.services.pdf_generator import InvoicePDFGenerator


class AllTemplatesRenderTest(TestCase):
    def setUp(self):
        user = CustomUser.objects.create_user(username='u', email='u@example.test', password='pw-12345678')
        self.company = Company.objects.create(user=user, owner=user, name='Acme Studio')

    def test_every_template_renders_a_pdf(self):
        for style in settings.INVOICE_TEMPLATES:
            with self.subTest(style=style):
                invoice = Invoice.objects.create(
                    company=self.company, invoice_number=f'INV-{style}', client_name='Globex',
                    invoice_date=date.today(), due_date=date.today(), template_style=style,
                )
                LineItem.objects.create(invoice=invoice, description='Design',
                                        quantity=Decimal('2'), rate=Decimal('150'))
                pdf = InvoicePDFGenerator(invoice).generate()
                self.assertTrue(pdf.startswith(b'%PDF'))
