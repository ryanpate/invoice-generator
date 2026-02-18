"""Tests for the ai_voice_generate view."""
import base64
import json
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

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
