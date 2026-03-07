"""
Tests for API v2 invoice CRUD endpoints.

Covers:
- List invoices (authenticated and unauthenticated)
- Create invoice with nested line items
- Retrieve invoice detail
- Update invoice (PUT and PATCH)
- Delete invoice
- Download PDF
- Mark as paid / mark as sent
- Toggle reminders / toggle late fees
- Make recurring (Professional tier required)
- Query param filters: ?status= and ?search=
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice, LineItem, RecurringInvoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INVOICES_URL = '/api/v2/invoices/'


def invoice_url(pk):
    return f'/api/v2/invoices/{pk}/'


def action_url(pk, action):
    return f'/api/v2/invoices/{pk}/{action}/'


def make_user(email='test@example.com', password='testpass123', tier='professional'):
    user = CustomUser.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password=password,
        subscription_tier=tier,
        subscription_status='active',
    )
    return user


def make_company(user, name='Test Co'):
    company, _ = Company.objects.get_or_create(
        user=user,
        defaults={'name': name},
    )
    return company


def make_invoice(company, **kwargs):
    defaults = dict(
        invoice_number='INV-00001',
        client_name='Test Client',
        client_email='client@example.com',
        invoice_date=timezone.now().date(),
        due_date=timezone.now().date(),
        payment_terms='net_30',
        currency='USD',
        status='draft',
    )
    defaults.update(kwargs)
    invoice = Invoice.objects.create(company=company, **defaults)
    LineItem.objects.create(
        invoice=invoice,
        description='Web development',
        quantity=Decimal('10.00'),
        rate=Decimal('150.00'),
        order=0,
    )
    invoice.calculate_totals()
    invoice.save()
    return invoice


def auth_client(user):
    """Return an APIClient authenticated with a valid JWT for *user*."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


# ---------------------------------------------------------------------------
# Fixtures mixin — creates a standard user + company + invoice
# ---------------------------------------------------------------------------

class InvoiceTestBase(TestCase):
    def setUp(self):
        self.user = make_user()
        self.company = make_company(self.user)
        self.invoice = make_invoice(self.company)
        self.client = auth_client(self.user)

    # ------------------------------------------------------------------
    # Convenience: valid create payload
    # ------------------------------------------------------------------

    @staticmethod
    def create_payload(**overrides):
        payload = {
            'client_name': 'New Client',
            'client_email': 'new@example.com',
            'invoice_date': timezone.now().date().isoformat(),
            'payment_terms': 'net_30',
            'currency': 'USD',
            'tax_rate': '0.00',
            'discount_amount': '0.00',
            'line_items': [
                {
                    'description': 'Consulting',
                    'quantity': '5.00',
                    'rate': '200.00',
                    'order': 0,
                }
            ],
        }
        payload.update(overrides)
        return payload


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------

class UnauthenticatedInvoiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # no credentials

    def test_list_returns_401(self):
        response = self.client.get(INVOICES_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_create_returns_401(self):
        response = self.client.post(INVOICES_URL, {}, format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_detail_returns_401(self):
        response = self.client.get('/api/v2/invoices/999/')
        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# List invoices
# ---------------------------------------------------------------------------

class InvoiceListTests(InvoiceTestBase):
    def test_list_returns_200_and_invoices(self):
        response = self.client.get(INVOICES_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # DRF pagination wraps results
        results = data.get('results', data)
        self.assertGreaterEqual(len(results), 1)

    def test_list_uses_list_serializer_fields(self):
        """List serializer must NOT include client_phone or line_items."""
        response = self.client.get(INVOICES_URL)
        results = response.json().get('results', response.json())
        first = results[0]
        self.assertIn('invoice_number', first)
        self.assertIn('currency_symbol', first)
        self.assertIn('reminders_paused', first)
        self.assertNotIn('line_items', first)
        self.assertNotIn('client_phone', first)

    def test_list_filtered_by_status(self):
        make_invoice(self.company, invoice_number='INV-00002', status='paid')
        response = self.client.get(INVOICES_URL, {'status': 'paid'})
        results = response.json().get('results', response.json())
        self.assertTrue(all(r['status'] == 'paid' for r in results))

    def test_list_filtered_by_search(self):
        make_invoice(
            self.company,
            invoice_number='INV-SEARCH-001',
            client_name='Unique Client XYZ',
        )
        response = self.client.get(INVOICES_URL, {'search': 'XYZ'})
        results = response.json().get('results', response.json())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['client_name'], 'Unique Client XYZ')

    def test_list_scoped_to_authenticated_user(self):
        """Invoices from another user must not appear."""
        other_user = make_user(email='other@example.com')
        other_company = make_company(other_user, name='Other Co')
        make_invoice(other_company, invoice_number='INV-OTHER-001')

        response = self.client.get(INVOICES_URL)
        results = response.json().get('results', response.json())
        invoice_numbers = [r['invoice_number'] for r in results]
        self.assertNotIn('INV-OTHER-001', invoice_numbers)


# ---------------------------------------------------------------------------
# Create invoice
# ---------------------------------------------------------------------------

class InvoiceCreateTests(InvoiceTestBase):
    def test_create_invoice_returns_201(self):
        payload = self.create_payload()
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 201, response.json())

    def test_create_invoice_persists_to_db(self):
        before = Invoice.objects.filter(company=self.company).count()
        self.client.post(INVOICES_URL, self.create_payload(), format='json')
        after = Invoice.objects.filter(company=self.company).count()
        self.assertEqual(after, before + 1)

    def test_create_invoice_with_line_items(self):
        payload = self.create_payload()
        payload['line_items'] = [
            {'description': 'Design', 'quantity': '2.00', 'rate': '300.00', 'order': 0},
            {'description': 'Dev', 'quantity': '8.00', 'rate': '150.00', 'order': 1},
        ]
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.json()['id'])
        self.assertEqual(invoice.line_items.count(), 2)

    def test_create_without_line_items_returns_400(self):
        payload = self.create_payload()
        payload['line_items'] = []
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('line_items', response.json())

    def test_create_with_invalid_template_returns_400(self):
        payload = self.create_payload(template_style='nonexistent_template')
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('template_style', response.json())

    def test_create_calculates_totals(self):
        payload = self.create_payload()
        payload['line_items'] = [
            {'description': 'Item', 'quantity': '4.00', 'rate': '100.00', 'order': 0}
        ]
        payload['tax_rate'] = '10.00'
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.json()['id'])
        # subtotal = 4 * 100 = 400; tax = 40; total = 440
        self.assertEqual(float(invoice.subtotal), 400.0)
        self.assertEqual(float(invoice.total), 440.0)

    def test_create_denied_when_invoice_limit_reached(self):
        self.user.subscription_tier = 'free'
        self.user.subscription_status = 'inactive'
        self.user.free_credits_remaining = 0
        self.user.credits_balance = 0
        self.user.save()

        payload = self.create_payload()
        response = self.client.post(INVOICES_URL, payload, format='json')
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Retrieve invoice detail
# ---------------------------------------------------------------------------

class InvoiceRetrieveTests(InvoiceTestBase):
    def test_retrieve_returns_200(self):
        response = self.client.get(invoice_url(self.invoice.pk))
        self.assertEqual(response.status_code, 200)

    def test_retrieve_includes_line_items(self):
        data = self.client.get(invoice_url(self.invoice.pk)).json()
        self.assertIn('line_items', data)
        self.assertGreater(len(data['line_items']), 0)

    def test_retrieve_includes_detail_fields(self):
        data = self.client.get(invoice_url(self.invoice.pk)).json()
        for field in ('client_phone', 'client_address', 'subtotal', 'tax_rate',
                      'tax_amount', 'discount_amount', 'notes', 'template_style',
                      'paid_at', 'sent_at', 'updated_at'):
            self.assertIn(field, data, f'Missing field: {field}')

    def test_retrieve_other_users_invoice_returns_404(self):
        other_user = make_user(email='other2@example.com')
        other_company = make_company(other_user, name='Other Co 2')
        other_invoice = make_invoice(other_company, invoice_number='INV-PRIV-001')

        response = self.client.get(invoice_url(other_invoice.pk))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Update invoice
# ---------------------------------------------------------------------------

class InvoiceUpdateTests(InvoiceTestBase):
    def test_put_update_returns_200(self):
        payload = self.create_payload(client_name='Updated Client')
        response = self.client.put(invoice_url(self.invoice.pk), payload, format='json')
        self.assertEqual(response.status_code, 200, response.json())

    def test_put_replaces_line_items(self):
        payload = self.create_payload()
        payload['line_items'] = [
            {'description': 'Only Item', 'quantity': '1.00', 'rate': '500.00', 'order': 0}
        ]
        self.client.put(invoice_url(self.invoice.pk), payload, format='json')
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.line_items.count(), 1)
        self.assertEqual(self.invoice.line_items.first().description, 'Only Item')

    def test_patch_update_returns_200(self):
        payload = {'client_name': 'Patched Client', 'line_items': [
            {'description': 'Patch Item', 'quantity': '1.00', 'rate': '100.00', 'order': 0}
        ]}
        response = self.client.patch(invoice_url(self.invoice.pk), payload, format='json')
        self.assertEqual(response.status_code, 200, response.json())

    def test_update_recalculates_totals(self):
        payload = self.create_payload()
        payload['line_items'] = [
            {'description': 'Single', 'quantity': '2.00', 'rate': '250.00', 'order': 0}
        ]
        payload['tax_rate'] = '0.00'
        self.client.put(invoice_url(self.invoice.pk), payload, format='json')
        self.invoice.refresh_from_db()
        self.assertEqual(float(self.invoice.total), 500.0)


# ---------------------------------------------------------------------------
# Delete invoice
# ---------------------------------------------------------------------------

class InvoiceDeleteTests(InvoiceTestBase):
    def test_delete_returns_204(self):
        response = self.client.delete(invoice_url(self.invoice.pk))
        self.assertEqual(response.status_code, 204)

    def test_delete_removes_from_db(self):
        pk = self.invoice.pk
        self.client.delete(invoice_url(pk))
        self.assertFalse(Invoice.objects.filter(pk=pk).exists())

    def test_delete_other_users_invoice_returns_404(self):
        other_user = make_user(email='other3@example.com')
        other_company = make_company(other_user, name='Other Co 3')
        other_invoice = make_invoice(other_company, invoice_number='INV-DEL-001')

        response = self.client.delete(invoice_url(other_invoice.pk))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

class InvoicePDFTests(InvoiceTestBase):
    @patch('apps.api_v2.views.invoices.InvoicePDFGenerator')
    def test_pdf_returns_200_with_pdf_content_type(self, mock_generator_class):
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'%PDF-1.4 fake content'
        mock_generator_class.return_value = mock_generator

        response = self.client.get(action_url(self.invoice.pk, 'pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(self.invoice.invoice_number, response['Content-Disposition'])

    @patch('apps.api_v2.views.invoices.InvoicePDFGenerator')
    def test_pdf_for_other_users_invoice_returns_404(self, mock_generator_class):
        other_user = make_user(email='pdfother@example.com')
        other_company = make_company(other_user, name='PDF Other Co')
        other_invoice = make_invoice(other_company, invoice_number='INV-PDF-001')

        response = self.client.get(action_url(other_invoice.pk, 'pdf'))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Mark as paid
# ---------------------------------------------------------------------------

class MarkPaidTests(InvoiceTestBase):
    def test_mark_paid_returns_200(self):
        response = self.client.post(action_url(self.invoice.pk, 'mark-paid'))
        self.assertEqual(response.status_code, 200)

    def test_mark_paid_changes_status(self):
        self.client.post(action_url(self.invoice.pk, 'mark-paid'))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_mark_paid_sets_paid_at(self):
        self.client.post(action_url(self.invoice.pk, 'mark-paid'))
        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.paid_at)

    def test_mark_paid_response_includes_status_field(self):
        data = self.client.post(action_url(self.invoice.pk, 'mark-paid')).json()
        self.assertEqual(data['status'], 'paid')


# ---------------------------------------------------------------------------
# Mark as sent
# ---------------------------------------------------------------------------

class MarkSentTests(InvoiceTestBase):
    def test_mark_sent_returns_200(self):
        response = self.client.post(action_url(self.invoice.pk, 'mark-sent'))
        self.assertEqual(response.status_code, 200)

    def test_mark_sent_changes_status(self):
        self.client.post(action_url(self.invoice.pk, 'mark-sent'))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'sent')

    def test_mark_sent_sets_sent_at(self):
        self.client.post(action_url(self.invoice.pk, 'mark-sent'))
        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.sent_at)

    def test_mark_sent_response_includes_status_field(self):
        data = self.client.post(action_url(self.invoice.pk, 'mark-sent')).json()
        self.assertEqual(data['status'], 'sent')


# ---------------------------------------------------------------------------
# Send invoice via email
# ---------------------------------------------------------------------------

class InvoiceSendEmailTests(InvoiceTestBase):
    @patch('apps.api_v2.views.invoices.InvoiceEmailService')
    def test_send_returns_200_on_success(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.get_default_subject.return_value = 'Invoice subject'
        mock_service.get_default_message.return_value = 'Invoice message'
        mock_service.send.return_value = {'success': True}
        mock_service_class.return_value = mock_service

        response = self.client.post(
            action_url(self.invoice.pk, 'send'),
            {'to_email': 'client@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        mock_service.send.assert_called_once()

    @patch('apps.api_v2.views.invoices.InvoiceEmailService')
    def test_send_returns_500_on_failure(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.get_default_subject.return_value = 'subject'
        mock_service.get_default_message.return_value = 'message'
        mock_service.send.return_value = {'success': False, 'error': 'SMTP error'}
        mock_service_class.return_value = mock_service

        response = self.client.post(
            action_url(self.invoice.pk, 'send'),
            {'to_email': 'client@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    def test_send_without_email_returns_400(self):
        # Remove client email from invoice so there's no fallback
        self.invoice.client_email = ''
        self.invoice.save()

        response = self.client.post(
            action_url(self.invoice.pk, 'send'),
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('to_email', response.json())


# ---------------------------------------------------------------------------
# Toggle reminders
# ---------------------------------------------------------------------------

class ToggleRemindersTests(InvoiceTestBase):
    def test_toggle_reminders_flips_false_to_true(self):
        self.invoice.reminders_paused = False
        self.invoice.save()

        response = self.client.post(action_url(self.invoice.pk, 'toggle-reminders'))
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.reminders_paused)

    def test_toggle_reminders_flips_true_to_false(self):
        self.invoice.reminders_paused = True
        self.invoice.save()

        response = self.client.post(action_url(self.invoice.pk, 'toggle-reminders'))
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertFalse(self.invoice.reminders_paused)

    def test_toggle_reminders_response_has_correct_keys(self):
        data = self.client.post(action_url(self.invoice.pk, 'toggle-reminders')).json()
        self.assertIn('reminders_paused', data)
        self.assertIn('invoice_id', data)
        self.assertEqual(data['invoice_id'], self.invoice.pk)


# ---------------------------------------------------------------------------
# Toggle late fees
# ---------------------------------------------------------------------------

class ToggleLateFeesTests(InvoiceTestBase):
    def test_toggle_late_fees_flips_false_to_true(self):
        self.invoice.late_fees_paused = False
        self.invoice.save()

        response = self.client.post(action_url(self.invoice.pk, 'toggle-late-fees'))
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.late_fees_paused)

    def test_toggle_late_fees_flips_true_to_false(self):
        self.invoice.late_fees_paused = True
        self.invoice.save()

        response = self.client.post(action_url(self.invoice.pk, 'toggle-late-fees'))
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertFalse(self.invoice.late_fees_paused)

    def test_toggle_late_fees_response_has_correct_keys(self):
        data = self.client.post(action_url(self.invoice.pk, 'toggle-late-fees')).json()
        self.assertIn('late_fees_paused', data)
        self.assertIn('invoice_id', data)


# ---------------------------------------------------------------------------
# Make recurring
# ---------------------------------------------------------------------------

class MakeRecurringTests(InvoiceTestBase):
    def test_make_recurring_returns_201(self):
        response = self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'monthly'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_make_recurring_creates_recurring_invoice(self):
        before = RecurringInvoice.objects.filter(company=self.company).count()
        self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'monthly'},
            format='json',
        )
        after = RecurringInvoice.objects.filter(company=self.company).count()
        self.assertEqual(after, before + 1)

    def test_make_recurring_copies_line_items(self):
        response = self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'weekly'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        recurring_id = response.json()['recurring_invoice_id']
        recurring = RecurringInvoice.objects.get(pk=recurring_id)
        self.assertEqual(
            recurring.line_items.count(),
            self.invoice.line_items.count(),
        )

    def test_make_recurring_response_has_required_fields(self):
        data = self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'monthly'},
            format='json',
        ).json()
        for field in ('recurring_invoice_id', 'name', 'frequency', 'start_date', 'next_run_date'):
            self.assertIn(field, data, f'Missing field: {field}')

    def test_make_recurring_invalid_frequency_returns_400(self):
        response = self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'fortnightly'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('frequency', response.json())

    def test_make_recurring_invalid_start_date_returns_400(self):
        response = self.client.post(
            action_url(self.invoice.pk, 'make-recurring'),
            {'frequency': 'monthly', 'start_date': 'not-a-date'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('start_date', response.json())

    def test_make_recurring_free_user_returns_403(self):
        """Free tier users must be denied recurring invoice creation."""
        free_user = make_user(email='free@example.com', tier='free')
        free_user.subscription_status = 'inactive'
        free_user.save()
        free_company = make_company(free_user, name='Free Co')
        free_invoice = make_invoice(free_company, invoice_number='INV-FREE-001')

        free_client = auth_client(free_user)
        response = free_client.post(
            action_url(free_invoice.pk, 'make-recurring'),
            {'frequency': 'monthly'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
