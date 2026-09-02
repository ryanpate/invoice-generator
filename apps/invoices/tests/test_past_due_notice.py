"""
Past-due notice: turn a computed late fee into a document that asks for money.

The late-fee calculators are the highest-intent pages on the site -- 56s and
five pageviews per person on the main one, 46s on the Florida page, against
1.3s on the homepage. Those visitors are business owners with an unpaid
invoice in front of them. Every CTA on those pages offered to help them
create a *new* invoice, which is not their problem; they want to collect on
one they already sent.

So: compute the fee, then generate a past-due notice carrying the original
amount, days overdue, the fee, the new total, and the state's rules.

DELIVERY IS TO THE VISITOR ONLY, DELIBERATELY. An anonymous form that mails
a debt-collection notice to an arbitrary third party from invoicekits.com is
a harassment and domain-reputation vector. The visitor gets the PDF and
sends it from their own mailbox, which is where a demand for payment should
come from anyway. test_never_emails_a_third_party pins that.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.invoices.models import TryLead


def valid_post(**overrides):
    due = date.today() - timedelta(days=45)
    data = {
        'business_name': 'Pate Design Studio',
        'client_name': 'Northwind Trading',
        'invoice_number': 'INV-2026-0042',
        'original_amount': '2400.00',
        'due_date': due.isoformat(),
        'late_fee': '108.00',
        'currency': 'USD',
        'state': '',
    }
    data.update(overrides)
    return data


class NoticePageTest(TestCase):
    """Public page, no login, prefilled from the calculator."""

    def test_page_is_public(self):
        self.assertEqual(self.client.get(reverse('past_due_notice')).status_code, 200)

    def test_prefills_from_the_calculator(self):
        response = self.client.get(
            reverse('past_due_notice'),
            {'amount': '2400.00', 'fee': '108.00', 'due_date': '2026-07-19', 'state': 'florida'},
        )
        html = response.content.decode()
        self.assertIn('value="2400.00"', html)
        self.assertIn('value="108.00"', html)
        self.assertIn('value="2026-07-19"', html)

    def test_junk_prefill_does_not_break_the_page(self):
        """The page has its own <script> block, so check for actual reflection."""
        response = self.client.get(
            reverse('past_due_notice'),
            {'amount': 'abc', 'fee': '<script>alert(1)</script>',
             'due_date': 'not-a-date', 'state': '../../etc/passwd'},
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('alert(1)', html)
        self.assertNotIn('etc/passwd', html)

    def test_says_it_is_not_legal_advice(self):
        """A demand for money must not imply we are giving legal advice."""
        html = self.client.get(reverse('past_due_notice')).content.decode()
        self.assertIn('not legal advice', html.lower())


class NoticePdfTest(TestCase):
    """The document itself."""

    def post(self, **overrides):
        return self.client.post(reverse('past_due_notice'), valid_post(**overrides))

    def test_returns_a_pdf_attachment(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertIn('past-due', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_filename_names_the_client(self):
        self.assertIn('northwind-trading', self.post()['Content-Disposition'].lower())

    def test_missing_required_fields_re_renders_not_500(self):
        response = self.client.post(reverse('past_due_notice'), {'business_name': 'Only this'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Content-Disposition', response.headers)

    def test_negative_amount_rejected(self):
        response = self.post(original_amount='-100')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Content-Disposition', response.headers)

    def test_future_due_date_rejected(self):
        """Nothing is past due if it is not yet due."""
        future = (date.today() + timedelta(days=10)).isoformat()
        response = self.post(due_date=future)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Content-Disposition', response.headers)


class NoticeMathTest(TestCase):
    """Days overdue and the new total must be right -- it is a demand for money."""

    def test_computes_days_overdue_and_total(self):
        from apps.invoices.services.past_due_notice import build_notice_context

        due = date.today() - timedelta(days=45)
        ctx = build_notice_context({
            'business_name': 'Pate Design', 'business_email': '',
            'client_name': 'Northwind', 'invoice_number': 'INV-1',
            'original_amount': Decimal('2400.00'), 'due_date': due,
            'late_fee': Decimal('108.00'), 'currency': 'USD',
            'state': '', 'notes': '',
        })
        self.assertEqual(ctx['days_overdue'], 45)
        self.assertEqual(ctx['total_due'], Decimal('2508.00'))
        self.assertEqual(ctx['currency_symbol'], '$')

    def test_state_rules_are_attached_when_a_state_is_chosen(self):
        from apps.invoices.services.past_due_notice import build_notice_context

        ctx = build_notice_context({
            'business_name': 'X', 'business_email': '', 'client_name': 'Y',
            'invoice_number': '', 'original_amount': Decimal('100'),
            'due_date': date.today() - timedelta(days=5),
            'late_fee': Decimal('5'), 'currency': 'USD',
            'state': 'florida', 'notes': '',
        })
        self.assertEqual(ctx['state_info']['name'], 'Florida')
        self.assertTrue(ctx['state_info']['statutes'])

    def test_unknown_state_is_ignored_not_fatal(self):
        from apps.invoices.services.past_due_notice import build_notice_context

        ctx = build_notice_context({
            'business_name': 'X', 'business_email': '', 'client_name': 'Y',
            'invoice_number': '', 'original_amount': Decimal('100'),
            'due_date': date.today() - timedelta(days=5),
            'late_fee': Decimal('5'), 'currency': 'USD',
            'state': 'atlantis', 'notes': '',
        })
        self.assertIsNone(ctx['state_info'])


class NoticeEmailTest(TestCase):
    """Email goes to the visitor. Never to anyone else."""

    def email_post(self, visitor_email='owner@example.test', **overrides):
        data = valid_post(**overrides)
        data['action'] = 'email'
        data['visitor_email'] = visitor_email
        return self.client.post(reverse('past_due_notice'), data)

    def test_emails_the_visitor_with_the_pdf_attached(self):
        response = self.email_post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['owner@example.test'])
        self.assertEqual(len(message.attachments), 1)
        self.assertTrue(message.attachments[0][0].endswith('.pdf'))

    def test_never_emails_a_third_party(self):
        """The safety property: no field may redirect delivery off the visitor.

        An anonymous endpoint that mails a debt-collection notice to an
        arbitrary address from our domain is a harassment vector. If this
        test ever fails, that door has been opened.
        """
        self.email_post(
            visitor_email='owner@example.test',
            client_email='victim@example.test',
            client_name='victim2@example.test',
            to='victim3@example.test',
            cc='victim4@example.test',
            bcc='victim5@example.test',
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        recipients = set(message.to) | set(message.cc) | set(message.bcc)
        self.assertEqual(recipients, {'owner@example.test'})
        for victim in ('victim@', 'victim2@', 'victim3@', 'victim4@', 'victim5@'):
            self.assertNotIn(victim, str(recipients))

    def test_invalid_visitor_email_rejected(self):
        response = self.email_post(visitor_email='not-an-email')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_captures_the_lead(self):
        self.email_post()
        self.assertTrue(TryLead.objects.filter(email='owner@example.test').exists())

    def test_is_rate_limited_per_session(self):
        for _ in range(6):
            self.email_post()
        self.assertLessEqual(
            len(mail.outbox), 3,
            'Anonymous notice email is not rate limited.',
        )


class CalculatorHandoffTest(TestCase):
    """The calculators must actually point at this."""

    def test_main_calculator_links_to_the_notice(self):
        html = self.client.get(reverse('late_fee_calculator')).content.decode()
        self.assertIn(reverse('past_due_notice'), html)

    def test_state_page_links_to_the_notice_with_its_state(self):
        html = self.client.get(
            reverse('state_late_fee_calculator', args=['florida'])
        ).content.decode()
        self.assertIn(reverse('past_due_notice'), html)
        self.assertIn('state=florida', html)
