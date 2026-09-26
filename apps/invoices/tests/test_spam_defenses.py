"""
Spam defenses, September 2026.

Bots used the no-login "email me this PDF" endpoints and unverified signups
to send junk invoices from noreply@invoicekits.com. These tests pin down the
limits that stop them.
"""
from datetime import date, timedelta

from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import AnonymousEmailSend, Invoice
from apps.invoices.services import anon_email_guard
from apps.invoices.services.email_sender import InvoiceEmailService
from apps.invoices.services.reminder_sender import PaymentReminderService

from .test_past_due_notice import valid_post as notice_post_data
from .test_try_draft import SocialAppsMixin, signup_post_data, try_post_data


def try_email(client, ip='203.0.113.1', **overrides):
    data = try_post_data(action='email', visitor_email='visitor@example.test')
    data.update(overrides)
    return client.post('/try/', data, HTTP_X_REAL_IP=ip)


class AnonymousEmailLimitTest(TestCase):
    def test_dropping_the_session_cookie_does_not_reset_the_limit(self):
        for _ in range(anon_email_guard.PER_IP_DAILY):
            # A fresh Client per request is a bot discarding its cookie.
            self.assertEqual(try_email(Client()).status_code, 200)
        self.assertEqual(try_email(Client()).status_code, 429)
        self.assertEqual(len(mail.outbox), anon_email_guard.PER_IP_DAILY)

    def test_one_recipient_is_capped_across_ips(self):
        for n in range(anon_email_guard.PER_RECIPIENT_DAILY):
            self.assertEqual(try_email(Client(), ip=f'203.0.113.{n + 10}').status_code, 200)
        self.assertEqual(try_email(Client(), ip='198.51.100.9').status_code, 429)

    def test_site_wide_cap_stops_a_bot_rotating_ips_and_addresses(self):
        AnonymousEmailSend.objects.bulk_create(
            AnonymousEmailSend(ip_address=f'10.0.{n // 250}.{n % 250}', recipient=f'r{n}@example.test')
            for n in range(anon_email_guard.SITE_WIDE_DAILY)
        )
        response = try_email(Client(), ip='198.51.100.77', visitor_email='new@example.test')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 0)

    def test_sends_older_than_a_day_do_not_count(self):
        AnonymousEmailSend.objects.bulk_create(
            AnonymousEmailSend(ip_address='203.0.113.1', recipient='visitor@example.test')
            for _ in range(anon_email_guard.PER_IP_DAILY)
        )
        AnonymousEmailSend.objects.update(created_at=timezone.now() - timedelta(days=2))
        self.assertEqual(try_email(Client()).status_code, 200)

    def test_past_due_notice_shares_the_same_limits(self):
        for _ in range(anon_email_guard.PER_IP_DAILY):
            try_email(Client())
        data = notice_post_data(action='email', visitor_email='other@example.test')
        response = Client().post(reverse('past_due_notice'), data, HTTP_X_REAL_IP='203.0.113.1')
        self.assertEqual(response.status_code, 429)


class HoneypotTest(TestCase):
    def test_try_bot_gets_fake_success_and_nothing_is_sent(self):
        response = try_email(self.client, website='http://spam.example')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(AnonymousEmailSend.objects.count(), 0)

    def test_past_due_bot_gets_fake_success_and_nothing_is_sent(self):
        data = notice_post_data(
            action='email', visitor_email='v@example.test', website='x'
        )
        response = self.client.post(reverse('past_due_notice'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_both_pages_render_the_honeypot(self):
        for url in ('/try/', reverse('past_due_notice')):
            self.assertContains(self.client.get(url), 'name="website"')


class NoVisitorTextInEmailTest(TestCase):
    SPAM = 'URGENT pay now at scam-example dot com'

    def test_try_email_subject_and_body_omit_client_name(self):
        try_email(self.client, client_name=self.SPAM)
        message = mail.outbox[0]
        self.assertNotIn(self.SPAM, message.subject)
        self.assertNotIn(self.SPAM, message.body)

    def test_past_due_email_subject_and_body_omit_free_text(self):
        data = notice_post_data(
            action='email', visitor_email='v@example.test',
            client_name=self.SPAM, invoice_number='CALL-555-0100',
        )
        self.client.post(reverse('past_due_notice'), data)
        message = mail.outbox[0]
        for text in (self.SPAM, 'CALL-555-0100'):
            self.assertNotIn(text, message.subject)
            self.assertNotIn(text, message.body)


@override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
class VerifiedSenderTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner', email='owner@example.test', password='pw-12345678'
        )
        company = Company.objects.create(user=self.user, owner=self.user, name='Bot Co')
        self.invoice = Invoice.objects.create(
            company=company,
            invoice_number='INV-1',
            client_name='Victim',
            client_email='victim@example.test',
            invoice_date=date.today(),
            due_date=date.today(),
            status='sent',
        )
        self.invoice.refresh_from_db()  # load DecimalField defaults as Decimals

    def test_unverified_owner_cannot_email_an_invoice(self):
        result = InvoiceEmailService(self.invoice).send(
            to_email='victim@example.test', subject='s', message='m'
        )
        self.assertFalse(result['success'])
        self.assertIn('verify your email', result['error'])
        self.assertEqual(len(mail.outbox), 0)

    def test_verified_owner_can_email_an_invoice(self):
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True
        )
        result = InvoiceEmailService(self.invoice).send(
            to_email='client@example.test', subject='s', message='m'
        )
        self.assertTrue(result['success'], result)
        self.assertEqual(len(mail.outbox), 1)

    def test_unverified_owner_receipt_skips_the_client(self):
        InvoiceEmailService(self.invoice).send_payment_receipt()
        recipients = {r for m in mail.outbox for r in m.to}
        self.assertNotIn('victim@example.test', recipients)

    def test_unverified_owner_cannot_send_reminders(self):
        result = PaymentReminderService(self.invoice).send_reminder(0)
        self.assertFalse(result['success'])
        self.assertEqual(len(mail.outbox), 0)


@override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
class MandatoryVerificationSignupTest(SocialAppsMixin, TestCase):
    def test_signup_sends_confirmation_and_does_not_log_in(self):
        response = self.client.post(reverse('account_signup'), signup_post_data())
        self.assertRedirects(
            response, reverse('account_email_verification_sent'),
            fetch_redirect_response=False,
        )
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(
            any('newuser@example.test' in m.to for m in mail.outbox)
        )

    def test_try_draft_is_still_saved_on_signup(self):
        self.client.post('/try/', try_post_data())
        self.client.post(reverse('account_signup'), signup_post_data())
        user = CustomUser.objects.get(email='newuser@example.test')
        self.assertTrue(Invoice.objects.filter(company__owner=user).exists())
