#!/usr/bin/env python
"""
Quick test script to verify watermark rendering in PDF templates.
Run with: python test_watermark.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa

def test_watermark():
    """Test that watermark renders in PDF template."""

    # Mock context data
    class MockCompany:
        name = "Test Company"
        logo = None
        address_line1 = "123 Test St"
        address_line2 = ""
        city = "Test City"
        state = "TS"
        postal_code = "12345"
        email = "test@example.com"
        phone = "555-1234"
        accent_color = "#3B82F6"

        class user:
            @staticmethod
            def shows_watermark():
                return True  # Simulate free tier

    class MockInvoice:
        invoice_number = "TEST-001"
        invoice_name = "Watermark Test Invoice"
        client_name = "Test Client"
        client_email = "client@example.com"
        client_phone = "555-5678"
        client_address = "456 Client Ave"
        invoice_date = "2024-01-15"
        due_date = "2024-02-15"
        payment_terms = "net_30"
        currency = "USD"
        subtotal = 1000.00
        tax_rate = 10
        tax_amount = 100.00
        total = 1100.00
        notes = "Thank you for your business!"
        template_style = "clean_slate"
        company = MockCompany()
        created_at = "2024-01-15 10:00:00"

        def get_payment_terms_display(self):
            return "Net 30"

        def get_currency_symbol(self):
            return "$"

    class MockLineItem:
        description = "Test Service"
        quantity = 10
        rate = 100.00
        amount = 1000.00

    context = {
        'invoice': MockInvoice(),
        'company': MockCompany(),
        'line_items': [MockLineItem()],
        'style': {
            'primary_color': '#1F2937',
            'accent_color': '#3B82F6',
            'background': '#FFFFFF',
            'text_color': '#1F2937',
            'font_family': 'Helvetica, sans-serif',
            'header_style': 'minimal',
        },
        'show_watermark': True,  # This is the key - should be True for free tier
        'currency_symbol': '$',
    }

    # Test each template
    templates = [
        'clean_slate',
        'classic_professional',
        'neon_edge'
    ]

    print("Testing watermark in PDF templates...\n")

    for template_name in templates:
        try:
            template_path = f'invoices/pdf/{template_name}.html'
            html_content = render_to_string(template_path, context)

            # Check if watermark HTML is in the rendered content
            has_watermark_container = 'watermark-container' in html_content
            has_watermark_div = 'class="watermark"' in html_content
            has_free_plan_text = 'FREE PLAN' in html_content

            status = "✓" if (has_watermark_container and has_watermark_div and has_free_plan_text) else "✗"
            print(f"{status} {template_name}:")
            print(f"   - Watermark container: {'Yes' if has_watermark_container else 'No'}")
            print(f"   - Watermark div: {'Yes' if has_watermark_div else 'No'}")
            print(f"   - FREE PLAN text: {'Yes' if has_free_plan_text else 'No'}")

            # Generate actual PDF to verify no errors
            result = BytesIO()
            pdf = pisa.CreatePDF(BytesIO(html_content.encode('utf-8')), dest=result)

            if pdf.err:
                print(f"   - PDF generation: FAILED ({pdf.err})")
            else:
                pdf_size = len(result.getvalue())
                print(f"   - PDF generation: OK ({pdf_size} bytes)")

                # Save test PDF
                output_file = f'test_watermark_{template_name}.pdf'
                with open(output_file, 'wb') as f:
                    f.write(result.getvalue())
                print(f"   - Saved to: {output_file}")

            print()

        except Exception as e:
            print(f"✗ {template_name}: ERROR - {e}\n")

    print("Test complete! Check the generated PDF files to verify watermarks visually.")

if __name__ == '__main__':
    test_watermark()
