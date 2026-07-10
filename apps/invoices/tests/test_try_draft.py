"""
Tests for carrying the /try/ draft invoice through signup.

A visitor who builds an invoice on /try/ and then signs up should find that
invoice saved to their new account instead of having to rebuild it.
"""
from datetime import date
from decimal import Decimal

from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from allauth.socialaccount.models import SocialApp

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice
from apps.invoices.views import TRY_DRAFT_SESSION_KEY, TRY_SAVED_INVOICE_SESSION_KEY


def try_post_data(**overrides):
    data = {
        'company_name': 'Acme Studio',
        'company_email': 'owner@acme.test',
        'client_name': 'Globex Corp',
        'client_email': 'billing@globex.test',
        'invoice_date': date.today().isoformat(),
        'payment_terms': 'net_30',
        'currency': 'USD',
        'tax_rate': '10',
        'template_style': 'clean_slate',
        'notes': 'Thanks for your business',
        'item_description_0': 'Design work',
        'item_quantity_0': '10',
        'item_rate_0': '150',
        'item_description_1': 'Consulting',
        'item_quantity_1': '2',
        'item_rate_1': '200',
    }
    data.update(overrides)
    return data


def signup_post_data(**overrides):
    data = {
        'email': 'newuser@example.test',
        'first_name': 'New',
        'last_name': 'User',
        'password1': 'sup3r-secret-pw!',
        'password2': 'sup3r-secret-pw!',
        'terms': 'on',
    }
    data.update(overrides)
    return data


class SocialAppsMixin:
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)


class TryDraftStashTest(SocialAppsMixin, TestCase):
    """Generating a PDF on /try/ stashes the draft in the session."""

    def test_valid_post_stashes_draft(self):
        response = self.client.post('/try/', try_post_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        draft = self.client.session.get(TRY_DRAFT_SESSION_KEY)
        self.assertIsNotNone(draft, 'draft was not stashed in the session')
        self.assertEqual(draft['company_name'], 'Acme Studio')
        self.assertEqual(draft['client_name'], 'Globex Corp')
        self.assertEqual(len(draft['line_items']), 2)
        self.assertEqual(draft['line_items'][0]['description'], 'Design work')

    def test_invalid_post_does_not_stash(self):
        data = try_post_data()
        for key in list(data):
            if key.startswith('item_'):
                del data[key]
        response = self.client.post('/try/', data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('application/pdf', response['Content-Type'])
        self.assertIsNone(self.client.session.get(TRY_DRAFT_SESSION_KEY))


class SignupRedemptionTest(SocialAppsMixin, TestCase):
    """Signing up with a stashed draft creates the company and invoice."""

    def stash_draft_then_sign_up(self, mutate_draft=None):
        self.client.post('/try/', try_post_data())
        if mutate_draft is not None:
            session = self.client.session
            session[TRY_DRAFT_SESSION_KEY] = mutate_draft(
                session[TRY_DRAFT_SESSION_KEY]
            )
            session.save()
        return self.client.post(reverse('account_signup'), signup_post_data())

    def test_signup_creates_company_and_invoice_from_draft(self):
        response = self.stash_draft_then_sign_up()
        self.assertEqual(response.status_code, 302)

        user = CustomUser.objects.get(email='newuser@example.test')
        company = Company.objects.get(owner=user)
        self.assertEqual(company.name, 'Acme Studio')

        invoice = Invoice.objects.get(company=company)
        self.assertEqual(invoice.client_name, 'Globex Corp')
        self.assertEqual(invoice.client_email, 'billing@globex.test')
        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(invoice.line_items.count(), 2)
        # 10*150 + 2*200 = 1900 subtotal, 10% tax -> 2090 total
        self.assertEqual(invoice.subtotal, Decimal('1900.00'))
        self.assertEqual(invoice.total, Decimal('2090.00'))

        # Draft consumed; saved pk recorded for the dashboard redirect
        self.assertIsNone(self.client.session.get(TRY_DRAFT_SESSION_KEY))
        self.assertEqual(
            self.client.session.get(TRY_SAVED_INVOICE_SESSION_KEY), invoice.pk
        )

    def test_signup_counts_toward_monthly_quota(self):
        self.stash_draft_then_sign_up()
        user = CustomUser.objects.get(email='newuser@example.test')
        self.assertEqual(user.invoices_created_this_month, 1)

    def test_signup_without_draft_is_unaffected(self):
        response = self.client.post(reverse('account_signup'), signup_post_data())
        self.assertEqual(response.status_code, 302)
        user = CustomUser.objects.get(email='newuser@example.test')
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertFalse(Company.objects.filter(owner=user).exists())

    def test_malformed_draft_does_not_break_signup(self):
        response = self.stash_draft_then_sign_up(
            mutate_draft=lambda draft: {'garbage': True}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CustomUser.objects.filter(email='newuser@example.test').exists()
        )
        self.assertEqual(Invoice.objects.count(), 0)


class DashboardRedirectTest(SocialAppsMixin, TestCase):
    """After redemption, the first dashboard visit lands on the new invoice."""

    def test_dashboard_redirects_to_saved_invoice_once(self):
        self.client.post('/try/', try_post_data())
        self.client.post(reverse('account_signup'), signup_post_data())

        invoice = Invoice.objects.get()
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(
            response, reverse('invoices:detail', kwargs={'pk': invoice.pk})
        )

        # One-shot: the next dashboard visit renders normally
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
