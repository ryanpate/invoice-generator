"""Tests for the ai_voice_generate view."""
import base64
import json
from unittest.mock import patch

from datetime import timedelta

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.invoices.models import GuestVoiceGeneration
from apps.invoices.services import guest_voice_guard

User = get_user_model()


class TestAiVoiceGenerateView(TestCase):
    """Tests for the /invoices/ai-voice-generate/ endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.url = reverse('invoices:ai_voice_generate')
        self.audio_data = base64.b64encode(b'fake-audio').decode('utf-8')
        self.valid_payload = json.dumps({
            'audio_data': self.audio_data,
            'media_type': 'audio/webm',
        })

    def test_requires_post(self):
        """GET request returns 405."""
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(self.url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 405)

    def test_requires_ajax(self):
        """Non-AJAX request returns 400."""
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post(self.url, self.valid_payload, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_guest_access_allowed(self):
        """Unauthenticated request is allowed (guest mode for /try/)."""
        resp = self.client.post(
            self.url,
            self.valid_payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        # Should not 302 redirect — view allows guests with session cap
        self.assertIn(resp.status_code, [200, 400])

    @patch('apps.invoices.services.ai_generator.AIInvoiceGenerator.generate_from_audio')
    def test_authenticated_success(self, mock_gen):
        """Authenticated user gets invoice data back."""
        mock_gen.return_value = {
            'success': True,
            'invoice_data': {
                'client_name': 'Test Client',
                'line_items': [{'description': 'Work', 'quantity': 1, 'unit_price': 100}],
                'transcript': 'Test transcript.',
            }
        }

        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post(
            self.url,
            self.valid_payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['invoice_data']['client_name'], 'Test Client')
        self.assertIn('remaining', data)

    @patch('apps.invoices.services.ai_generator.AIInvoiceGenerator.generate_from_audio')
    def test_guest_session_cap(self, mock_gen):
        """Guest is capped at 1 voice generation per session."""
        mock_gen.return_value = {
            'success': True,
            'invoice_data': {
                'line_items': [{'description': 'Work', 'quantity': 1, 'unit_price': 50}],
                'transcript': 'Work.',
            }
        }

        # First request — should succeed
        resp1 = self.client.post(
            self.url,
            self.valid_payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertTrue(resp1.json()['success'])

        # Second request — should be capped
        resp2 = self.client.post(
            self.url,
            self.valid_payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertFalse(resp2.json()['success'])
        self.assertIn('sign up', resp2.json()['error'].lower())

    def test_missing_audio_data(self):
        """Returns error when audio_data is missing."""
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post(
            self.url,
            json.dumps({'media_type': 'audio/webm'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertFalse(data['success'])


@patch('apps.invoices.services.ai_generator.AIInvoiceGenerator.generate_from_audio')
class GuestVoiceLimitTest(TestCase):
    """
    The guest cap was one per session cookie, so a bot that dropped its cookie
    could send unlimited audio to Claude. Guest use is now counted in the
    database per IP and site-wide over 24 hours.
    """

    def setUp(self):
        self.url = reverse('invoices:ai_voice_generate')
        self.payload = json.dumps({
            'audio_data': base64.b64encode(b'fake-audio').decode('utf-8'),
            'media_type': 'audio/webm',
        })

    def post(self, ip='203.0.113.1'):
        # A fresh Client per request is a bot discarding its cookie.
        return Client().post(
            self.url, self.payload, content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_X_REAL_IP=ip,
        ).json()

    def test_dropping_the_session_cookie_does_not_reset_the_limit(self, mock_gen):
        mock_gen.return_value = {'success': True, 'invoice_data': {}}
        for _ in range(guest_voice_guard.PER_IP_DAILY):
            self.assertTrue(self.post()['success'])
        self.assertFalse(self.post()['success'])
        self.assertEqual(mock_gen.call_count, guest_voice_guard.PER_IP_DAILY)

    def test_failed_generations_still_count(self, mock_gen):
        mock_gen.return_value = {'success': False, 'error': 'upstream error'}
        for _ in range(guest_voice_guard.PER_IP_DAILY + 2):
            self.post()
        self.assertEqual(mock_gen.call_count, guest_voice_guard.PER_IP_DAILY)

    def test_site_wide_cap_stops_a_bot_rotating_ips(self, mock_gen):
        mock_gen.return_value = {'success': True, 'invoice_data': {}}
        GuestVoiceGeneration.objects.bulk_create(
            GuestVoiceGeneration(ip_address=f'10.0.0.{n}')
            for n in range(guest_voice_guard.SITE_WIDE_DAILY)
        )
        self.assertFalse(self.post(ip='198.51.100.77')['success'])
        mock_gen.assert_not_called()

    def test_uses_older_than_a_day_do_not_count(self, mock_gen):
        mock_gen.return_value = {'success': True, 'invoice_data': {}}
        GuestVoiceGeneration.objects.bulk_create(
            GuestVoiceGeneration(ip_address='203.0.113.1')
            for _ in range(guest_voice_guard.PER_IP_DAILY)
        )
        GuestVoiceGeneration.objects.update(created_at=timezone.now() - timedelta(days=2))
        self.assertTrue(self.post()['success'])

