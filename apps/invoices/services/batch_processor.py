"""
Batch invoice processing service.
"""
import csv
import zipfile
from io import BytesIO, StringIO
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.core.files.base import ContentFile
from django.utils import timezone

from ..models import Invoice, LineItem, InvoiceBatch
# PDF generator imported lazily to avoid WeasyPrint startup issues


class CSVValidationError(Exception):
    """Custom exception for CSV validation errors."""
    pass


class BatchInvoiceProcessor:
    """Process CSV files to create multiple invoices."""

    REQUIRED_COLUMNS = ['client_name', 'item_description', 'quantity', 'rate']
    OPTIONAL_COLUMNS = [
        'client_email', 'client_phone', 'client_address',
        'tax_rate', 'currency', 'payment_terms', 'notes'
    ]

    def __init__(self, batch: InvoiceBatch):
        self.batch = batch
        self.company = batch.company
        self.errors = []
        self.invoices_created = []

    def validate_csv(self, csv_content: str) -> list:
        """Validate CSV structure and data."""
        self.errors = []

        try:
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)
        except Exception as e:
            raise CSVValidationError(f"Failed to parse CSV: {str(e)}")

        if not rows:
            raise CSVValidationError("CSV file is empty")

        # Check required columns
        headers = rows[0].keys() if rows else []
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in headers]
        if missing_columns:
            raise CSVValidationError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

        # Validate each row
        validated_rows = []
        for row_num, row in enumerate(rows, start=2):
            row_errors = self._validate_row(row, row_num)
            if row_errors:
                self.errors.extend(row_errors)
            else:
                validated_rows.append(row)

        if self.errors:
            raise CSVValidationError(
                f"Validation errors:\n" + "\n".join(self.errors)
            )

        return validated_rows

    def _validate_row(self, row: dict, row_num: int) -> list:
        """Validate a single CSV row."""
        errors = []

        # Required field validation
        if not row.get('client_name', '').strip():
            errors.append(f"Row {row_num}: client_name is required")

        if not row.get('item_description', '').strip():
            errors.append(f"Row {row_num}: item_description is required")

        # Numeric field validation
        try:
            quantity = Decimal(row.get('quantity', '0'))
            if quantity <= 0:
                errors.append(f"Row {row_num}: quantity must be positive")
        except InvalidOperation:
            errors.append(f"Row {row_num}: invalid quantity value")

        try:
            rate = Decimal(row.get('rate', '0'))
            if rate < 0:
                errors.append(f"Row {row_num}: rate cannot be negative")
        except InvalidOperation:
            errors.append(f"Row {row_num}: invalid rate value")

        if row.get('tax_rate'):
            try:
                tax_rate = Decimal(row.get('tax_rate', '0'))
                if tax_rate < 0 or tax_rate > 100:
                    errors.append(f"Row {row_num}: tax_rate must be between 0 and 100")
            except InvalidOperation:
                errors.append(f"Row {row_num}: invalid tax_rate value")

        return errors

    def group_by_client(self, rows: list) -> dict:
        """Group rows by client to create one invoice per client."""
        clients = {}

        for row in rows:
            client_name = row['client_name'].strip()

            if client_name not in clients:
                clients[client_name] = {
                    'client_name': client_name,
                    'client_email': row.get('client_email', '').strip(),
                    'client_phone': row.get('client_phone', '').strip(),
                    'client_address': row.get('client_address', '').strip(),
                    'tax_rate': row.get('tax_rate', str(self.company.default_tax_rate)),
                    'currency': row.get('currency', self.company.default_currency),
                    'payment_terms': row.get('payment_terms', self.company.default_payment_terms),
                    'notes': row.get('notes', self.company.default_notes),
                    'line_items': []
                }

            clients[client_name]['line_items'].append({
                'description': row['item_description'].strip(),
                'quantity': Decimal(row['quantity']),
                'rate': Decimal(row['rate']),
            })

        return clients

    def create_invoice_from_data(self, client_data: dict) -> Invoice:
        """Create an invoice from grouped client data."""
        # Generate invoice number
        invoice_number = self.company.get_next_invoice_number()

        # Create invoice
        invoice = Invoice.objects.create(
            company=self.company,
            invoice_number=invoice_number,
            client_name=client_data['client_name'],
            client_email=client_data['client_email'],
            client_phone=client_data['client_phone'],
            client_address=client_data['client_address'],
            invoice_date=timezone.now().date(),
            payment_terms=client_data['payment_terms'],
            currency=client_data['currency'],
            tax_rate=Decimal(client_data['tax_rate'] or '0'),
            notes=client_data['notes'],
            template_style=self.company.default_template,
        )

        # Create line items
        for idx, item_data in enumerate(client_data['line_items']):
            LineItem.objects.create(
                invoice=invoice,
                description=item_data['description'],
                quantity=item_data['quantity'],
                rate=item_data['rate'],
                order=idx
            )

        # Recalculate totals and set due date
        invoice.due_date = invoice.calculate_due_date()
        invoice.calculate_totals()
        invoice.save()

        return invoice

    def process(self) -> dict:
        """Process the batch CSV file."""
        self.batch.status = 'processing'
        self.batch.save(update_fields=['status'])

        try:
            # Read CSV file
            self.batch.csv_file.seek(0)
            csv_content = self.batch.csv_file.read().decode('utf-8')

            # Validate CSV
            validated_rows = self.validate_csv(csv_content)

            # Group by client
            clients = self.group_by_client(validated_rows)
            self.batch.total_invoices = len(clients)
            self.batch.save(update_fields=['total_invoices'])

            # Check if user can create this many invoices
            user = self.company.user
            for _ in clients:
                if not user.can_create_invoice():
                    raise CSVValidationError(
                        "Invoice limit reached for your plan. "
                        "Please upgrade to create more invoices."
                    )

            # Create invoices
            pdf_files = []
            # Lazy import to avoid WeasyPrint startup issues
            from .pdf_generator import InvoicePDFGenerator

            for client_name, client_data in clients.items():
                try:
                    invoice = self.create_invoice_from_data(client_data)
                    self.invoices_created.append(invoice)

                    # Generate PDF (may fail if WeasyPrint deps not installed)
                    try:
                        generator = InvoicePDFGenerator(invoice)
                        generator.save_to_invoice()
                    except RuntimeError:
                        # PDF generation unavailable, continue without PDF
                        pass

                    # Collect PDF for zip (if generated)
                    if invoice.pdf_file:
                        invoice.pdf_file.seek(0)
                        pdf_files.append((
                            f"{invoice.invoice_number}.pdf",
                            invoice.pdf_file.read()
                        ))

                    # Increment user's invoice count
                    user.increment_invoice_count()

                    self.batch.processed_invoices += 1
                    self.batch.save(update_fields=['processed_invoices'])

                except Exception as e:
                    self.batch.failed_invoices += 1
                    self.batch.save(update_fields=['failed_invoices'])
                    self.errors.append(f"Failed to create invoice for {client_name}: {str(e)}")

            # Create ZIP file
            if pdf_files:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, pdf_content in pdf_files:
                        zip_file.writestr(filename, pdf_content)

                zip_buffer.seek(0)
                zip_filename = f"invoices_batch_{self.batch.id}.zip"
                self.batch.zip_file.save(zip_filename, ContentFile(zip_buffer.read()))

            self.batch.status = 'completed'
            self.batch.completed_at = timezone.now()
            self.batch.save()

            return {
                'success': True,
                'total': self.batch.total_invoices,
                'processed': self.batch.processed_invoices,
                'failed': self.batch.failed_invoices,
                'errors': self.errors,
                'invoices': self.invoices_created,
            }

        except CSVValidationError as e:
            self.batch.status = 'failed'
            self.batch.error_message = str(e)
            self.batch.save()
            return {
                'success': False,
                'error': str(e),
            }

        except Exception as e:
            self.batch.status = 'failed'
            self.batch.error_message = str(e)
            self.batch.save()
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
            }

    def get_summary(self) -> dict:
        """Get processing summary."""
        return {
            'batch_id': self.batch.id,
            'status': self.batch.status,
            'total_invoices': self.batch.total_invoices,
            'processed_invoices': self.batch.processed_invoices,
            'failed_invoices': self.batch.failed_invoices,
            'errors': self.errors,
            'zip_url': self.batch.zip_file.url if self.batch.zip_file else None,
        }


def get_csv_template() -> str:
    """Generate a sample CSV template for batch uploads."""
    headers = [
        'client_name', 'client_email', 'client_phone', 'client_address',
        'item_description', 'quantity', 'rate', 'tax_rate', 'currency',
        'payment_terms', 'notes'
    ]

    sample_rows = [
        [
            'Acme Corporation', 'billing@acme.com', '+1 555-0100', '123 Business Ave, New York, NY 10001',
            'Website Development', '40', '150', '8.5', 'USD', 'net_30', 'Thank you for your business!'
        ],
        [
            'Acme Corporation', 'billing@acme.com', '+1 555-0100', '123 Business Ave, New York, NY 10001',
            'SEO Optimization', '10', '100', '8.5', 'USD', 'net_30', 'Thank you for your business!'
        ],
        [
            'Tech Startup Inc', 'finance@techstartup.io', '+1 555-0200', '456 Innovation Blvd, San Francisco, CA 94102',
            'Mobile App Design', '60', '175', '0', 'USD', 'net_15', ''
        ],
    ]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(sample_rows)

    return output.getvalue()
