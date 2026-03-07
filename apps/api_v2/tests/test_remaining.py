"""
Tests for API v2 recurring, company, settings, billing, and client endpoints.

Covers:
- Recurring invoices: list, create, retrieve, update, delete, toggle_status, generate_now
- Company: GET and PUT
- Settings: reminder_settings (GET/PUT), late_fee_settings (GET/PATCH)
- Billing: usage, entitlements, device registration, Apple receipt stub, Apple notifications
- Client analytics: client_stats with and without history
"""
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import (
    Invoice,
    LineItem,
    RecurringInvoice,
    RecurringLineItem,
    PaymentReminderSettings,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_user(
    email='user@example.com',
    password='testpass123',
    tier='professional',
    status='active',
):
    return CustomUser.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password=password,
        subscription_tier=tier,
        subscription_status=status,
    )


def make_company(user, name='Test Co'):
    company, _ = Company.objects.get_or_create(
        user=user,
        defaults={'name': name},
    )
    return company


def auth_client(user):
    """Return an APIClient with a valid JWT Bearer token for *user*."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


def make_recurring(company, **kwargs):
    """Create a RecurringInvoice with a single line item."""
    defaults = dict(
        name='Monthly Retainer',
        client_name='Acme Corp',
        client_email='acme@example.com',
        frequency='monthly',
        start_date=timezone.now().date(),
        next_run_date=timezone.now().date(),
        currency='USD',
        payment_terms='net_30',
        status='active',
    )
    defaults.update(kwargs)
    recurring = RecurringInvoice.objects.create(company=company, **defaults)
    RecurringLineItem.objects.create(
        recurring_invoice=recurring,
        description='Consulting',
        quantity=Decimal('1.00'),
        rate=Decimal('500.00'),
        order=0,
    )
    return recurring


def make_paid_invoice(company, client_email, days_to_pay=10):
    """Create a sent-then-paid invoice to build client payment history."""
    from datetime import timedelta
    invoice = Invoice.objects.create(
        company=company,
        invoice_number=f'INV-HIST-{company.pk}',
        client_name='History Client',
        client_email=client_email,
        invoice_date=timezone.now().date() - timedelta(days=days_to_pay + 5),
        due_date=timezone.now().date() - timedelta(days=5),
        payment_terms='net_30',
        currency='USD',
        status='paid',
        sent_at=timezone.now() - timedelta(days=days_to_pay + 5),
        paid_at=timezone.now() - timedelta(days=5),
    )
    LineItem.objects.create(
        invoice=invoice,
        description='Work',
        quantity=Decimal('1.00'),
        rate=Decimal('200.00'),
        order=0,
    )
    invoice.calculate_totals()
    invoice.save()
    return invoice


# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

RECURRING_URL = '/api/v2/recurring/'
COMPANY_URL = '/api/v2/company/'
REMINDERS_URL = '/api/v2/settings/reminders/'
LATE_FEES_URL = '/api/v2/settings/late-fees/'
USAGE_URL = '/api/v2/billing/usage/'
ENTITLEMENTS_URL = '/api/v2/billing/entitlements/'
APPLE_RECEIPT_URL = '/api/v2/billing/apple/verify-receipt/'
DEVICE_URL = '/api/v2/billing/device/register/'
APPLE_NOTIF_URL = '/api/v2/billing/apple/notifications/'
CLIENT_STATS_URL = '/api/v2/clients/stats/'


def recurring_url(pk):
    return f'/api/v2/recurring/{pk}/'


def recurring_action_url(pk, action):
    return f'/api/v2/recurring/{pk}/{action}/'


# ===========================================================================
# Module 1 — Recurring Invoices
# ===========================================================================

class RecurringInvoiceListTests(TestCase):
    def setUp(self):
        self.user = make_user(tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)

    def test_list_returns_200_and_recurring_invoices(self):
        make_recurring(self.company)
        make_recurring(self.company, name='Quarterly Report', frequency='quarterly')
        response = self.client.get(RECURRING_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)

    def test_list_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(RECURRING_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_list_free_tier_returns_403(self):
        free_user = make_user(email='free@example.com', tier='free', status='inactive')
        c = auth_client(free_user)
        response = c.get(RECURRING_URL)
        self.assertEqual(response.status_code, 403)

    def test_list_only_shows_own_recurring_invoices(self):
        other_user = make_user(email='other@example.com', tier='professional')
        other_company = make_company(other_user, 'Other Co')
        make_recurring(other_company, name='Other Recurring')

        make_recurring(self.company, name='My Recurring')
        response = self.client.get(RECURRING_URL)
        self.assertEqual(response.status_code, 200)
        names = [r['name'] for r in response.json()['results']]
        self.assertIn('My Recurring', names)
        self.assertNotIn('Other Recurring', names)


class RecurringInvoiceCreateTests(TestCase):
    def setUp(self):
        self.user = make_user(tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)

    def _payload(self, **overrides):
        payload = {
            'name': 'Monthly Design Retainer',
            'client_name': 'Globex Corp',
            'client_email': 'globex@example.com',
            'frequency': 'monthly',
            'start_date': str(timezone.now().date()),
            'currency': 'USD',
            'payment_terms': 'net_30',
            'line_items': [
                {'description': 'Design work', 'quantity': '1.00', 'rate': '2000.00', 'order': 0},
            ],
        }
        payload.update(overrides)
        return payload

    def test_create_valid_recurring_returns_201(self):
        response = self.client.post(RECURRING_URL, self._payload(), format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['name'], 'Monthly Design Retainer')
        self.assertEqual(data['frequency'], 'monthly')
        self.assertEqual(len(data['line_items']), 1)
        self.assertTrue(RecurringInvoice.objects.filter(company=self.company).exists())

    def test_create_without_line_items_returns_400(self):
        payload = self._payload()
        payload['line_items'] = []
        response = self.client.post(RECURRING_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_missing_required_field_returns_400(self):
        payload = self._payload()
        del payload['client_name']
        response = self.client.post(RECURRING_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_invalid_frequency_returns_400(self):
        payload = self._payload(frequency='daily')
        response = self.client.post(RECURRING_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)


class RecurringInvoiceDetailTests(TestCase):
    def setUp(self):
        self.user = make_user(tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)
        self.recurring = make_recurring(self.company)

    def test_retrieve_returns_full_detail_with_line_items(self):
        response = self.client.get(recurring_url(self.recurring.pk))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], self.recurring.pk)
        self.assertIn('line_items', data)
        self.assertEqual(len(data['line_items']), 1)
        self.assertIn('amount', data['line_items'][0])

    def test_retrieve_other_users_recurring_returns_404(self):
        other_user = make_user(email='other2@example.com', tier='professional')
        other_company = make_company(other_user, 'Other Co2')
        other_recurring = make_recurring(other_company)
        response = self.client.get(recurring_url(other_recurring.pk))
        self.assertEqual(response.status_code, 404)

    def test_update_recurring_replaces_line_items(self):
        payload = {
            'name': 'Updated Retainer',
            'client_name': 'Acme Corp',
            'client_email': 'acme@example.com',
            'frequency': 'quarterly',
            'start_date': str(timezone.now().date()),
            'currency': 'USD',
            'payment_terms': 'net_30',
            'line_items': [
                {'description': 'New work', 'quantity': '2.00', 'rate': '750.00', 'order': 0},
                {'description': 'Extra', 'quantity': '1.00', 'rate': '100.00', 'order': 1},
            ],
        }
        response = self.client.put(recurring_url(self.recurring.pk), payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Updated Retainer')
        self.assertEqual(data['frequency'], 'quarterly')
        self.assertEqual(len(data['line_items']), 2)

    def test_delete_recurring_returns_204(self):
        response = self.client.delete(recurring_url(self.recurring.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(RecurringInvoice.objects.filter(pk=self.recurring.pk).exists())


class RecurringToggleStatusTests(TestCase):
    def setUp(self):
        self.user = make_user(tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)
        self.recurring = make_recurring(self.company, status='active')

    def test_toggle_active_to_paused(self):
        response = self.client.post(recurring_action_url(self.recurring.pk, 'toggle-status'))
        self.assertEqual(response.status_code, 200)
        self.recurring.refresh_from_db()
        self.assertEqual(self.recurring.status, 'paused')

    def test_toggle_paused_to_active(self):
        self.recurring.pause()
        response = self.client.post(recurring_action_url(self.recurring.pk, 'toggle-status'))
        self.assertEqual(response.status_code, 200)
        self.recurring.refresh_from_db()
        self.assertEqual(self.recurring.status, 'active')

    def test_toggle_cancelled_returns_400(self):
        self.recurring.cancel()
        response = self.client.post(recurring_action_url(self.recurring.pk, 'toggle-status'))
        self.assertEqual(response.status_code, 400)


class RecurringGenerateNowTests(TestCase):
    def setUp(self):
        self.user = make_user(tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)
        self.recurring = make_recurring(self.company)

    def test_generate_now_creates_invoice_returns_201(self):
        response = self.client.post(recurring_action_url(self.recurring.pk, 'generate-now'))
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('generated_invoice_id', data)
        self.assertIn('invoice_number', data)
        # The recurring counter should have incremented
        self.assertEqual(data['invoices_generated'], 1)

    def test_generate_now_cancelled_returns_400(self):
        self.recurring.cancel()
        response = self.client.post(recurring_action_url(self.recurring.pk, 'generate-now'))
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Module 2 — Company
# ===========================================================================

class CompanyDetailTests(TestCase):
    def setUp(self):
        self.user = make_user(email='co@example.com', tier='starter')
        self.company = make_company(self.user, 'My Agency')
        self.client = auth_client(self.user)

    def test_get_company_returns_200(self):
        response = self.client.get(COMPANY_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'My Agency')
        self.assertIn('email', data)
        self.assertIn('late_fees_enabled', data)

    def test_get_creates_company_if_missing(self):
        """Users without a company should still get a 200 with an auto-created company."""
        new_user = make_user(email='nocompany@example.com', tier='starter')
        c = auth_client(new_user)
        response = c.get(COMPANY_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('name', data)

    def test_put_updates_company(self):
        payload = {
            'name': 'Updated Agency',
            'email': 'agency@example.com',
            'phone': '555-1234',
            'website': 'https://example.com',
            'address_line1': '123 Main St',
            'address_line2': '',
            'city': 'Austin',
            'state': 'TX',
            'postal_code': '78701',
            'country': 'United States',
            'tax_id': '12-3456789',
            'default_currency': 'USD',
            'default_payment_terms': 'net_30',
            'default_tax_rate': '8.25',
            'default_template': 'clean_slate',
            'default_notes': 'Thanks for your business.',
            'accent_color': '#1D4ED8',
            'invoice_prefix': 'INV-',
            'late_fees_enabled': False,
            'late_fee_type': 'flat',
            'late_fee_amount': '0.00',
            'late_fee_grace_days': 3,
        }
        response = self.client.put(COMPANY_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Updated Agency')
        self.assertEqual(data['city'], 'Austin')
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Updated Agency')

    def test_patch_partial_update(self):
        response = self.client.patch(COMPANY_URL, {'name': 'Patched Co'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Patched Co')
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Patched Co')

    def test_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(COMPANY_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_logo_url_is_none_when_no_logo(self):
        response = self.client.get(COMPANY_URL)
        self.assertIsNone(response.json()['logo_url'])

    def test_upload_logo_missing_file_returns_400(self):
        response = self.client.post('/api/v2/company/logo/', {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_signature_missing_file_returns_400(self):
        response = self.client.post('/api/v2/company/signature/', {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_remove_logo_when_no_logo_returns_204(self):
        response = self.client.delete('/api/v2/company/logo/remove/')
        self.assertEqual(response.status_code, 204)

    def test_remove_signature_when_no_signature_returns_204(self):
        response = self.client.delete('/api/v2/company/signature/remove/')
        self.assertEqual(response.status_code, 204)


# ===========================================================================
# Module 3 — Settings
# ===========================================================================

class ReminderSettingsTests(TestCase):
    def setUp(self):
        self.user = make_user(email='reminders@example.com', tier='starter')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)

    def test_get_reminder_settings_returns_200(self):
        response = self.client.get(REMINDERS_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Default values
        self.assertIn('reminders_enabled', data)
        self.assertFalse(data['reminders_enabled'])
        self.assertIn('remind_3_days_before', data)

    def test_get_creates_settings_if_missing(self):
        """PaymentReminderSettings is created on first GET if absent."""
        self.assertFalse(
            PaymentReminderSettings.objects.filter(company=self.company).exists()
        )
        response = self.client.get(REMINDERS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            PaymentReminderSettings.objects.filter(company=self.company).exists()
        )

    def test_put_updates_reminder_settings(self):
        payload = {
            'reminders_enabled': True,
            'remind_3_days_before': True,
            'remind_1_day_before': False,
            'remind_on_due_date': True,
            'remind_3_days_after': True,
            'remind_7_days_after': False,
            'remind_14_days_after': False,
            'cc_business_owner': True,
            'custom_message_before': 'Your invoice is due soon.',
            'custom_message_due': 'Your invoice is due today.',
            'custom_message_overdue': 'Your invoice is overdue.',
        }
        response = self.client.put(REMINDERS_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['reminders_enabled'])
        self.assertTrue(data['cc_business_owner'])
        self.assertFalse(data['remind_1_day_before'])

    def test_patch_partial_update(self):
        response = self.client.patch(REMINDERS_URL, {'reminders_enabled': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['reminders_enabled'])

    def test_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(REMINDERS_URL)
        self.assertIn(response.status_code, [401, 403])


class LateFeeSettingsTests(TestCase):
    def setUp(self):
        self.user = make_user(email='latefees@example.com', tier='starter')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)

    def test_get_late_fee_settings_returns_200(self):
        response = self.client.get(LATE_FEES_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('late_fees_enabled', data)
        self.assertIn('late_fee_type', data)
        self.assertIn('late_fee_grace_days', data)

    def test_patch_updates_late_fee_settings(self):
        payload = {
            'late_fees_enabled': True,
            'late_fee_type': 'percentage',
            'late_fee_amount': '1.50',
            'late_fee_grace_days': 5,
        }
        response = self.client.patch(LATE_FEES_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['late_fees_enabled'])
        self.assertEqual(data['late_fee_type'], 'percentage')
        self.assertEqual(Decimal(data['late_fee_amount']), Decimal('1.50'))
        self.company.refresh_from_db()
        self.assertTrue(self.company.late_fees_enabled)

    def test_put_full_update(self):
        payload = {
            'late_fees_enabled': True,
            'late_fee_type': 'flat',
            'late_fee_amount': '25.00',
            'late_fee_grace_days': 7,
            'late_fee_max_amount': None,
        }
        response = self.client.put(LATE_FEES_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['late_fee_amount'], '25.00')


# ===========================================================================
# Module 4 — Billing
# ===========================================================================

class UsageViewTests(TestCase):
    def setUp(self):
        self.user = make_user(email='usage@example.com', tier='professional')
        self.client = auth_client(self.user)

    def test_usage_returns_200_for_subscriber(self):
        response = self.client.get(USAGE_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('subscription_tier', data)
        self.assertIn('invoices', data)
        self.assertIn('api_calls', data)
        self.assertIn('ai_generations', data)
        self.assertEqual(data['subscription_tier'], 'professional')

    def test_usage_invoice_fields_for_subscriber(self):
        response = self.client.get(USAGE_URL)
        invoices = response.json()['invoices']
        self.assertIn('used', invoices)
        self.assertIn('limit', invoices)
        self.assertIn('percentage', invoices)

    def test_usage_returns_credits_for_free_user(self):
        free_user = make_user(
            email='free_usage@example.com',
            tier='free',
            status='inactive',
        )
        c = auth_client(free_user)
        response = c.get(USAGE_URL)
        self.assertEqual(response.status_code, 200)
        invoices = response.json()['invoices']
        # Free users see credits, not monthly quota
        self.assertIn('free_credits_remaining', invoices)
        self.assertIn('total_credits', invoices)

    def test_usage_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(USAGE_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_usage_ai_generations_unlimited_for_professional(self):
        response = self.client.get(USAGE_URL)
        ai = response.json()['ai_generations']
        # Professional has unlimited AI generations
        self.assertIsNone(ai.get('limit'))
        self.assertTrue(ai['unlimited'])


class EntitlementsViewTests(TestCase):
    def setUp(self):
        self.user = make_user(email='ent@example.com', tier='business')
        self.client = auth_client(self.user)

    def test_entitlements_returns_200(self):
        response = self.client.get(ENTITLEMENTS_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('subscription_tier', data)
        self.assertIn('features', data)
        self.assertIn('available_templates', data)

    def test_entitlements_business_tier_features(self):
        response = self.client.get(ENTITLEMENTS_URL)
        features = response.json()['features']
        self.assertTrue(features['recurring_invoices'])
        self.assertTrue(features['team_seats'])
        self.assertTrue(features['batch_upload'])

    def test_entitlements_free_tier_limited(self):
        free_user = make_user(email='free_ent@example.com', tier='free', status='inactive')
        c = auth_client(free_user)
        response = c.get(ENTITLEMENTS_URL)
        self.assertEqual(response.status_code, 200)
        features = response.json()['features']
        self.assertFalse(features['recurring_invoices'])
        self.assertFalse(features['team_seats'])
        self.assertFalse(features['batch_upload'])

    def test_entitlements_shows_available_templates(self):
        response = self.client.get(ENTITLEMENTS_URL)
        templates = response.json()['available_templates']
        self.assertIsInstance(templates, list)
        self.assertGreater(len(templates), 0)

    def test_entitlements_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(ENTITLEMENTS_URL)
        self.assertIn(response.status_code, [401, 403])


class DeviceTokenRegistrationTests(TestCase):
    def setUp(self):
        self.user = make_user(email='device@example.com', tier='professional')
        self.client = auth_client(self.user)

    def test_register_device_creates_token_returns_201(self):
        payload = {
            'token': 'abc123devicetoken456',
            'platform': 'ios',
        }
        response = self.client.post(DEVICE_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['token'], 'abc123devicetoken456')
        self.assertEqual(data['platform'], 'ios')
        self.assertTrue(data['is_active'])
        self.assertTrue(data['created'])

    def test_register_device_idempotent_returns_200(self):
        payload = {'token': 'same-token-xyz', 'platform': 'ios'}
        self.client.post(DEVICE_URL, payload, format='json')
        response = self.client.post(DEVICE_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['created'])

    def test_register_device_android_platform(self):
        payload = {'token': 'android-fcm-token', 'platform': 'android'}
        response = self.client.post(DEVICE_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['platform'], 'android')

    def test_register_device_missing_token_returns_400(self):
        response = self.client.post(DEVICE_URL, {'platform': 'ios'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_device_invalid_platform_returns_400(self):
        payload = {'token': 'some-token', 'platform': 'windows'}
        response = self.client.post(DEVICE_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_device_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.post(DEVICE_URL, {'token': 'x', 'platform': 'ios'}, format='json')
        self.assertIn(response.status_code, [401, 403])


class AppleReceiptVerificationTests(TestCase):
    def setUp(self):
        self.user = make_user(email='apple@example.com', tier='free', status='inactive')
        self.client = auth_client(self.user)

    def test_verify_known_product_upgrades_tier(self):
        payload = {
            'transaction_jws': 'eyJzdHViIjoidHJ1ZSJ9',
            'product_id': 'com.invoicekits.professional.monthly',
        }
        response = self.client.post(APPLE_RECEIPT_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['subscription_tier'], 'professional')
        self.assertEqual(data['payment_source'], 'apple')
        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, 'professional')
        self.assertEqual(self.user.payment_source, 'apple')

    def test_verify_business_product(self):
        payload = {
            'transaction_jws': 'eyJzdHViIjoidHJ1ZSJ9',
            'product_id': 'com.invoicekits.business.annual',
        }
        response = self.client.post(APPLE_RECEIPT_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['subscription_tier'], 'business')

    def test_verify_unknown_product_returns_400(self):
        payload = {
            'transaction_jws': 'eyJzdHViIjoidHJ1ZSJ9',
            'product_id': 'com.invoicekits.unknown',
        }
        response = self.client.post(APPLE_RECEIPT_URL, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_verify_missing_fields_returns_400(self):
        response = self.client.post(APPLE_RECEIPT_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_verify_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.post(
            APPLE_RECEIPT_URL,
            {'transaction_jws': 'x', 'product_id': 'com.invoicekits.professional.monthly'},
            format='json',
        )
        self.assertIn(response.status_code, [401, 403])


class AppleServerNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_notification_with_signed_payload_returns_200(self):
        """Apple notification endpoint is AllowAny and should return 200 immediately."""
        payload = {'signedPayload': 'eyJzdHViIjoidHJ1ZSJ9.test.stub'}
        response = self.client.post(APPLE_NOTIF_URL, payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_notification_missing_payload_returns_400(self):
        response = self.client.post(APPLE_NOTIF_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_notification_no_auth_required(self):
        """Endpoint is AllowAny — Apple servers don't send auth tokens."""
        payload = {'signedPayload': 'some.jws.string'}
        response = self.client.post(APPLE_NOTIF_URL, payload, format='json')
        # Must not be 401/403
        self.assertNotIn(response.status_code, [401, 403])


# ===========================================================================
# Module 5 — Client Analytics
# ===========================================================================

class ClientStatsTests(TestCase):
    def setUp(self):
        self.user = make_user(email='analytics@example.com', tier='professional')
        self.company = make_company(self.user)
        self.client = auth_client(self.user)

    def test_missing_email_returns_400(self):
        response = self.client.get(CLIENT_STATS_URL)
        self.assertEqual(response.status_code, 400)

    def test_new_client_no_history(self):
        response = self.client.get(CLIENT_STATS_URL, {'email': 'brand@new.com'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['has_history'])
        self.assertIsNone(data['rating'])
        self.assertIn('description', data)

    def test_client_with_payment_history_returns_rating(self):
        client_email = 'goodpayer@client.com'
        # Paid in 10 days → should be A or B
        make_paid_invoice(self.company, client_email=client_email, days_to_pay=10)

        response = self.client.get(CLIENT_STATS_URL, {'email': client_email})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['has_history'])
        self.assertIsNotNone(data['rating'])
        self.assertIn(data['rating'], ['A', 'B', 'C', 'D', 'F'])
        self.assertIn('stats', data)

    def test_stats_includes_totals_as_strings(self):
        """Decimal values must be serialised as strings for JSON safety."""
        client_email = 'paid@client.com'
        make_paid_invoice(self.company, client_email=client_email, days_to_pay=5)

        response = self.client.get(CLIENT_STATS_URL, {'email': client_email})
        self.assertEqual(response.status_code, 200)
        stats = response.json()['stats']
        # total_paid should be a stringified decimal, not a Python Decimal object
        self.assertIsInstance(stats['total_paid'], str)
        self.assertIsInstance(stats['outstanding_amount'], str)

    def test_stats_scoped_to_authenticated_users_company(self):
        """Analytics should only reflect the requesting user's invoices."""
        other_user = make_user(email='other_analytics@example.com', tier='professional')
        other_company = make_company(other_user, 'Other Analytics Co')
        shared_email = 'shared@client.com'

        # Create invoice in OTHER company — should not appear for self.user
        make_paid_invoice(other_company, client_email=shared_email, days_to_pay=3)

        response = self.client.get(CLIENT_STATS_URL, {'email': shared_email})
        self.assertEqual(response.status_code, 200)
        # self.user has no invoices for this client, so no history
        self.assertFalse(response.json()['has_history'])

    def test_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get(CLIENT_STATS_URL, {'email': 'x@x.com'})
        self.assertIn(response.status_code, [401, 403])

    def test_email_returned_in_response(self):
        email = 'echo@test.com'
        response = self.client.get(CLIENT_STATS_URL, {'email': email})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['email'], email)
