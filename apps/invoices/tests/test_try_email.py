"""
Tests for /try/ email capture — "Email me this PDF".

A visitor who won't sign up can enter their email to receive the watermarked
PDF. The email is recorded as a lead, and the draft still carries through
signup if they convert later.
"""
from django.core import mail
from django.test import TestCase

from apps.invoices.models import TryLead
from apps.invoices.views import TRY_DRAFT_SESSION_KEY

from .test_try_draft import try_post_data


def email_post_data(**overrides):
    data = try_post_data()
    data['action'] = 'email'
    data['visitor_email'] = 'visitor@example.test'
    data.update(overrides)
    return data


class TryEmailSendTest(TestCase):
    def test_valid_request_emails_pdf_and_records_lead(self):
        response = self.client.post('/try/', email_post_data())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['visitor@example.test'])
        filename, content, mimetype = message.attachments[0]
        self.assertTrue(filename.endswith('.pdf'))
        self.assertEqual(mimetype, 'application/pdf')
        self.assertTrue(content[:4] in (b'%PDF', '%PDF'))

        lead = TryLead.objects.get(email='visitor@example.test')
        self.assertEqual(lead.send_count, 1)

    def test_email_path_also_stashes_draft_for_signup(self):
        self.client.post('/try/', email_post_data())
        draft = self.client.session.get(TRY_DRAFT_SESSION_KEY)
        self.assertIsNotNone(draft)
        self.assertEqual(draft['client_name'], 'Globex Corp')

    def test_invalid_email_rejected(self):
        response = self.client.post(
            '/try/', email_post_data(visitor_email='not-an-email')
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(TryLead.objects.count(), 0)

    def test_missing_line_items_rejected_as_json(self):
        data = email_post_data()
        for key in list(data):
            if key.startswith('item_'):
                del data[key]
        response = self.client.post('/try/', data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(len(mail.outbox), 0)

    def test_session_capped_at_three_sends(self):
        for _ in range(3):
            response = self.client.post('/try/', email_post_data())
            self.assertEqual(response.status_code, 200)
        response = self.client.post('/try/', email_post_data())
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()['success'])
        self.assertEqual(len(mail.outbox), 3)

    def test_repeat_email_updates_single_lead(self):
        self.client.post('/try/', email_post_data())
        self.client.post('/try/', email_post_data())
        self.assertEqual(TryLead.objects.count(), 1)
        self.assertEqual(
            TryLead.objects.get(email='visitor@example.test').send_count, 2
        )
