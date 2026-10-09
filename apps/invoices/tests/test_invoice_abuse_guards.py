"""
Free-generation and scam guards, October 2026.

Users were producing invoices without paying, and some looked like scams:
  - a free account could edit one invoice to bill a new client, re-download
    or re-send it, and repeat forever (editing was never metered);
  - /try/ and the past-due notice tool had no download limit at all;
  - nothing stopped a fake "Geek Squad renewal, call to cancel" invoice.
"""
from datetime import date
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.companies.forms import CompanyForm
from apps.companies.models import Company
from apps.invoices.forms import LineItemFormSet
from apps.invoices.models import Invoice, LineItem
from apps.invoices.services import guest_pdf_guard, scam_guard
from apps.invoices.services.invoice_quota import is_new_client
from apps.invoices.views import TRY_DRAFT_SESSION_KEY, TryInvoiceView

from .test_past_due_notice import valid_post as notice_post_data
from .test_try_draft import try_post_data


class ScamPatternTest(TestCase):
    def test_brand_as_sender_is_blocked(self):
        for name in ['Geek Squad', 'PayPal', 'Norton LifeLock', 'McAfee Total Protection',
                     'Best Buy Billing Dept', 'paypal inc.']:
            self.assertTrue(scam_guard.looks_like_scam(name, []), name)

    def test_real_businesses_sharing_a_word_with_a_brand_pass(self):
        for name in ['Norton Electric', 'Apple Orchard Farms', 'Amazonia Landscaping',
                     'Acme Studio', 'Best Buys Consulting']:
            self.assertFalse(scam_guard.looks_like_scam(name, []), name)

    def test_phone_plus_callback_language_is_blocked(self):
        self.assertTrue(scam_guard.looks_like_scam('Acme', [
            'Annual renewal processed. If you did not authorize this charge call +1 (888) 555-0100'
        ]))

    def test_phone_or_refund_wording_alone_passes(self):
        self.assertFalse(scam_guard.looks_like_scam('Acme', ['Questions? Call (555) 123-4567']))
        self.assertFalse(scam_guard.looks_like_scam('Acme', ['No refunds after 30 days']))
        self.assertFalse(scam_guard.looks_like_scam('Acme', ['PayPal integration, 10 hours']))
        self.assertFalse(scam_guard.looks_like_scam('Acme', [
            'Domain renewal, 1 year', 'Hosting 2026-10-01 to 2026-10-31',
            'Questions? Call (555) 123-4567. Cancellation fee applies after 48h.',
        ]))


class TryPageGuardTest(TestCase):
    def test_downloads_are_capped_per_ip_even_without_cookies(self):
        for _ in range(guest_pdf_guard.PER_IP_DAILY):
            response = Client().post('/try/', try_post_data(), HTTP_X_REAL_IP='203.0.113.9')
            self.assertEqual(response['Content-Type'], 'application/pdf')
        response = Client().post('/try/', try_post_data(), HTTP_X_REAL_IP='203.0.113.9')
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'limit for free previews', status_code=429)
        # A different visitor is unaffected.
        response = Client().post('/try/', try_post_data(), HTTP_X_REAL_IP='203.0.113.10')
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_scam_invoice_is_refused(self):
        response = self.client.post('/try/', try_post_data(company_name='Geek Squad'))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['Content-Type'], 'application/pdf')
        self.assertContains(response, 'payment scams')

    def test_scam_invoice_is_not_emailed(self):
        response = self.client.post('/try/', try_post_data(
            action='email', visitor_email='v@example.test',
            notes='Auto-renewal charged. To cancel this subscription call 1-888-555-0100',
        ))
        self.assertEqual(response.status_code, 400)

    def test_line_items_are_capped(self):
        data = try_post_data()
        for i in range(2, 120):
            data.update({f'item_description_{i}': 'x', f'item_quantity_{i}': '1',
                         f'item_rate_{i}': '1'})
        response = self.client.post('/try/', data)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        draft = self.client.session[TRY_DRAFT_SESSION_KEY]
        self.assertEqual(len(draft['line_items']), TryInvoiceView.MAX_LINE_ITEMS)


class PastDueNoticeGuardTest(TestCase):
    def test_downloads_share_the_guest_cap(self):
        for _ in range(guest_pdf_guard.PER_IP_DAILY):
            Client().post('/try/', try_post_data(), HTTP_X_REAL_IP='203.0.113.9')
        response = Client().post(reverse('past_due_notice'), notice_post_data(),
                                 HTTP_X_REAL_IP='203.0.113.9')
        self.assertEqual(response.status_code, 429)

    def test_scam_notice_is_refused(self):
        response = self.client.post(reverse('past_due_notice'),
                                    notice_post_data(business_name='PayPal'))
        self.assertNotEqual(response['Content-Type'], 'application/pdf')
        self.assertContains(response, 'payment scams')


class IsNewClientTest(TestCase):
    def test_typo_fixes_are_not_a_new_client(self):
        self.assertFalse(is_new_client('Jon Smith', '', 'John Smith', ''))
        self.assertFalse(is_new_client('Globex Corp', 'a@globex.test', 'Globex Corp.', 'A@Globex.test'))

    def test_different_client_is_new(self):
        self.assertTrue(is_new_client('Globex', '', 'Initech', ''))
        self.assertTrue(is_new_client('Globex', 'a@globex.test', 'Globex', 'b@other.test'))
        self.assertTrue(is_new_client('Globex', 'a@globex.test', 'Globex', ''))


class FreeInvoiceReuseTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='free', email='free@example.test', password='pw-12345678'
        )
        self.company = Company.objects.create(user=self.user, owner=self.user, name='Acme Studio')
        self.invoice = Invoice.objects.create(
            company=self.company, invoice_number='INV-1', client_name='Globex',
            client_email='billing@globex.test', invoice_date=date.today(), due_date=date.today(),
        )
        self.item = LineItem.objects.create(
            invoice=self.invoice, description='Design', quantity=Decimal('1'), rate=Decimal('100')
        )
        self.client.force_login(self.user)

    def edit(self, **overrides):
        prefix = LineItemFormSet().prefix
        data = {
            'client_name': 'Globex', 'client_email': 'billing@globex.test',
            'invoice_date': date.today().isoformat(), 'payment_terms': 'net_30',
            'currency': 'USD', 'tax_rate': '0', 'template_style': 'clean_slate',
            f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '1',
            f'{prefix}-MIN_NUM_FORMS': '1', f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-id': str(self.item.pk), f'{prefix}-0-description': 'Design',
            f'{prefix}-0-quantity': '1', f'{prefix}-0-rate': '100',
        }
        data.update(overrides)
        return self.client.post(reverse('invoices:edit', args=[self.invoice.pk]), data)

    def set_used(self, count):
        self.user.invoices_created_this_month = count
        self.user.save()

    def test_editing_amounts_for_the_same_client_is_free(self):
        self.set_used(3)
        response = self.edit(**{f'{LineItemFormSet().prefix}-0-rate': '250'})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.invoices_created_this_month, 3)

    def test_retargeting_counts_as_a_new_invoice(self):
        self.set_used(1)
        response = self.edit(client_name='Initech', client_email='ap@initech.test')
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.invoices_created_this_month, 2)

    def test_retargeting_is_refused_at_the_limit(self):
        self.set_used(3)
        response = self.edit(client_name='Initech', client_email='ap@initech.test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Changing the client makes this a new invoice')
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.client_name, 'Globex')

    def test_paid_plans_edit_freely(self):
        self.user.subscription_tier = 'professional'
        self.user.subscription_status = 'active'
        self.user.save()
        self.set_used(3)
        response = self.edit(client_name='Initech', client_email='ap@initech.test')
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.invoices_created_this_month, 3)

    def test_scam_text_is_refused_on_edit(self):
        response = self.edit(notes='If you did not authorize this charge call +1 888 555 0100')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'payment scams')


class ApiV2ReuseTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient

        self.user = CustomUser.objects.create_user(
            username='free', email='free@example.test', password='pw-12345678',
            invoices_created_this_month=3,
        )
        company = Company.objects.create(user=self.user, owner=self.user, name='Acme Studio')
        self.invoice = Invoice.objects.create(
            company=company, invoice_number='INV-1', client_name='Globex',
            client_email='billing@globex.test', invoice_date=date.today(), due_date=date.today(),
        )
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_retargeting_at_the_limit_is_refused(self):
        response = self.api.patch(f'/api/v2/invoices/{self.invoice.pk}/',
                                  {'client_name': 'Initech', 'client_email': 'ap@initech.test'},
                                  format='json')
        self.assertEqual(response.status_code, 403)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.client_name, 'Globex')

    def test_same_client_edit_is_allowed(self):
        response = self.api.patch(f'/api/v2/invoices/{self.invoice.pk}/',
                                  {'notes': 'Thanks!'}, format='json')
        self.assertEqual(response.status_code, 200)


class CompanyNameTest(TestCase):
    def test_brand_company_name_is_rejected(self):
        form = CompanyForm(data={'name': 'Geek Squad Support'})
        form.is_valid()
        self.assertIn('name', form.errors)

    def test_ordinary_company_name_passes_name_check(self):
        form = CompanyForm(data={'name': 'Norton Electric'})
        form.is_valid()
        self.assertNotIn('name', form.errors)
