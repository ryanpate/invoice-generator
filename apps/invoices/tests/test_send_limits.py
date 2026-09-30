"""
Logged-in invoice email limits, September 2026.

One signed-in account looped POST /invoices/<id>/send/ at ~3.6 sends a second
for four hours. The send had no cap and took a free-form recipient, CC,
subject and message, so it worked as a spam relay. These tests pin down the
per-account caps and the fixed email content on the free tier.
"""
from datetime import date, timedelta

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice, InvoiceEmailSend
from apps.invoices.services.email_sender import PER_INVOICE_DAILY, InvoiceEmailService

SPAM = 'WIN A PRIZE http://spam.example'


class SendLimitTestCase(TestCase):
    tier = 'free'

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner', email='owner@example.test', password='pw-12345678',
            subscription_tier=self.tier, subscription_status='active',
        )
        self.company = Company.objects.create(user=self.user, owner=self.user, name='Real Co')
        self.invoice = self.make_invoice('INV-1')

    def make_invoice(self, number):
        invoice = Invoice.objects.create(
            company=self.company,
            invoice_number=number,
            client_name='Client',
            client_email='client@example.test',
            invoice_date=date.today(),
            due_date=date.today(),
            status='sent',
        )
        invoice.refresh_from_db()  # load DecimalField defaults as Decimals
        return invoice

    def send(self, invoice=None, **overrides):
        kwargs = {'to_email': 'client@example.test', 'subject': 's', 'message': 'm'}
        kwargs.update(overrides)
        return InvoiceEmailService(invoice or self.invoice).send(**kwargs)

    def fill(self, count, invoice=None):
        InvoiceEmailSend.objects.bulk_create(
            InvoiceEmailSend(user=self.user, invoice=invoice, recipient=f'r{n}@example.test')
            for n in range(count)
        )


class DailySendCapTest(SendLimitTestCase):
    def test_account_is_capped_per_day(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['free'])
        result = self.send()
        self.assertFalse(result['success'])
        self.assertIn('limit', result['error'])
        self.assertEqual(len(mail.outbox), 0)

    def test_cap_is_shared_across_invoices(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['free'], invoice=self.invoice)
        self.assertFalse(self.send(invoice=self.make_invoice('INV-2'))['success'])

    def test_sends_older_than_a_day_do_not_count(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['free'])
        InvoiceEmailSend.objects.update(created_at=timezone.now() - timedelta(days=2))
        self.assertTrue(self.send()['success'])

    def test_a_successful_send_is_recorded(self):
        self.assertTrue(self.send()['success'])
        sent = InvoiceEmailSend.objects.get()
        self.assertEqual((sent.user, sent.invoice, sent.recipient),
                         (self.user, self.invoice, 'client@example.test'))

    def test_deleting_the_invoice_does_not_reset_the_count(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['free'], invoice=self.invoice)
        self.invoice.delete()
        self.assertFalse(self.send(invoice=self.make_invoice('INV-2'))['success'])


class PaidSendCapTest(SendLimitTestCase):
    tier = 'professional'

    def test_paid_tier_has_a_higher_cap(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['free'])
        self.assertTrue(self.send()['success'])

    def test_one_invoice_is_capped_per_day(self):
        self.fill(PER_INVOICE_DAILY, invoice=self.invoice)
        self.assertFalse(self.send()['success'])
        self.assertTrue(self.send(invoice=self.make_invoice('INV-2'))['success'])

    def test_every_cc_address_counts_toward_the_cap(self):
        self.fill(settings.INVOICE_EMAIL_DAILY_LIMITS['professional'] - 2)
        result = self.send(cc_emails=['a@example.test', 'b@example.test'])
        self.assertFalse(result['success'])
        self.assertEqual(len(mail.outbox), 0)

    def test_paid_tier_keeps_custom_subject_message_and_cc(self):
        self.send(subject='Custom subject', message='Custom body', cc_emails=['cc@example.test'])
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Custom subject')
        self.assertIn('Custom body', message.body)
        self.assertEqual(message.cc, ['cc@example.test'])

    def test_lapsed_subscription_gets_the_free_rules(self):
        CustomUser.objects.filter(pk=self.user.pk).update(subscription_status='canceled')
        self.invoice.refresh_from_db()
        self.send(subject=SPAM, message=SPAM, cc_emails=['cc@example.test'])
        message = mail.outbox[0]
        self.assertNotIn(SPAM, message.subject)
        self.assertEqual(message.cc, [])


class FreeTierFixedContentTest(SendLimitTestCase):
    def test_free_tier_cannot_set_subject_message_or_cc(self):
        result = self.send(subject=SPAM, message=SPAM, cc_emails=['cc@example.test'])
        self.assertTrue(result['success'], result)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Invoice INV-1 from Real Co')
        self.assertNotIn(SPAM, message.body)
        self.assertEqual(message.cc, [])

    def test_send_page_hides_the_free_text_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('invoices:send_email', args=[self.invoice.pk]))
        self.assertContains(response, 'name="to_email"')
        for field in ('cc_emails', 'subject', 'message'):
            self.assertNotContains(response, f'name="{field}"')

    def test_send_page_posts_with_only_a_recipient(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('invoices:send_email', args=[self.invoice.pk]),
            {'to_email': 'client@example.test', 'subject': SPAM, 'message': SPAM},
        )
        self.assertRedirects(
            response, reverse('invoices:detail', args=[self.invoice.pk]),
            fetch_redirect_response=False,
        )
        self.assertNotIn(SPAM, mail.outbox[0].subject)


class PaidSendPageTest(SendLimitTestCase):
    tier = 'professional'

    def test_send_page_keeps_the_free_text_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('invoices:send_email', args=[self.invoice.pk]))
        for field in ('to_email', 'cc_emails', 'subject', 'message'):
            self.assertContains(response, f'name="{field}"')
