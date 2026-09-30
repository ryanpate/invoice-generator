"""
The public invoice link used to let anyone holding it mark the invoice paid,
which sent receipts and stopped reminders and late fees with no payment. It
now only tells the owner the client says they have paid.
"""
from datetime import date, timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice


class PublicReportPaidTest(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner', email='owner@example.test', password='pw-12345678'
        )
        company = Company.objects.create(user=self.owner, owner=self.owner, name='Real Co')
        self.invoice = Invoice.objects.create(
            company=company,
            invoice_number='INV-1',
            client_name='Client',
            client_email='client@example.test',
            invoice_date=date.today(),
            due_date=date.today(),
            status='sent',
        )
        self.url = reverse('invoices:public_mark_paid', args=[self.invoice.public_token])

    def test_status_is_not_changed(self):
        self.client.post(self.url)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'sent')
        self.assertIsNone(self.invoice.paid_at)

    def test_owner_is_emailed_and_the_client_is_not(self):
        self.client.post(self.url)
        self.assertEqual([m.to for m in mail.outbox], [['owner@example.test']])
        self.assertIn('INV-1', mail.outbox[0].subject)

    def test_repeat_reports_within_a_day_send_one_email(self):
        for _ in range(3):
            response = self.client.post(self.url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertTrue(response.json()['success'])
        self.assertEqual(len(mail.outbox), 1)

    def test_a_report_after_a_day_notifies_again(self):
        self.client.post(self.url)
        Invoice.objects.filter(pk=self.invoice.pk).update(
            payment_reported_at=timezone.now() - timedelta(days=2)
        )
        self.client.post(self.url)
        self.assertEqual(len(mail.outbox), 2)

    def test_paid_invoice_cannot_be_reported(self):
        Invoice.objects.filter(pk=self.invoice.pk).update(status='paid')
        self.assertEqual(self.client.post(self.url).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_public_page_offers_report_not_mark_paid(self):
        response = self.client.get(
            reverse('invoices:public_invoice', args=[self.invoice.public_token])
        )
        self.assertContains(response, "I've paid this")
        self.assertNotContains(response, 'Mark as Paid')

    def test_public_page_shows_a_note_once_reported(self):
        self.client.post(self.url)
        response = self.client.get(
            reverse('invoices:public_invoice', args=[self.invoice.public_token])
        )
        self.assertContains(response, 'Payment reported')
        self.assertNotContains(response, "I've paid this")
