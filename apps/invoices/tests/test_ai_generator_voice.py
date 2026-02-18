"""Tests for voice-to-invoice AI generation."""
import base64
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.invoices.services.ai_generator import AIInvoiceGenerator

User = get_user_model()


class TestGenerateFromAudio(TestCase):
    """Tests for AIInvoiceGenerator.generate_from_audio()"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.generator = AIInvoiceGenerator(self.user)
        self.audio_data = base64.b64encode(b'fake-audio-data').decode('utf-8')
        self.media_type = 'audio/webm'

    @patch.object(AIInvoiceGenerator, '_call_claude_audio_api')
    def test_successful_generation(self, mock_api):
        """Returns structured invoice data from valid audio."""
        mock_api.return_value = {
            'client_name': 'John Smith',
            'client_email': None,
            'client_phone': None,
            'client_address': '123 Main St',
            'invoice_name': None,
            'payment_terms': 'net_30',
            'currency': 'USD',
            'tax_rate': None,
            'notes': None,
            'line_items': [
                {'description': 'Logo design', 'quantity': 1, 'unit_price': 500.00}
            ],
            'transcript': 'Invoice John Smith at 123 Main St, $500 for logo design, net 30.'
        }

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertTrue(result['success'])
        self.assertEqual(result['invoice_data']['client_name'], 'John Smith')
        self.assertEqual(len(result['invoice_data']['line_items']), 1)
        self.assertEqual(result['invoice_data']['line_items'][0]['unit_price'], 500.00)
        self.assertIn('transcript', result['invoice_data'])

    @patch.object(AIInvoiceGenerator, '_call_claude_audio_api')
    def test_no_line_items_returns_error(self, mock_api):
        """Returns error when Claude extracts no line items."""
        mock_api.return_value = {
            'client_name': 'John',
            'line_items': [],
            'transcript': 'Something about John.'
        }

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertFalse(result['success'])
        self.assertIn('extract', result['error'].lower())

    @patch.object(AIInvoiceGenerator, '_call_claude_audio_api')
    def test_api_returns_none_on_error(self, mock_api):
        """Returns error when API call fails."""
        mock_api.return_value = None

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertFalse(result['success'])

    def test_invalid_media_type_rejected(self):
        """Rejects unsupported audio media types."""
        result = self.generator.generate_from_audio(self.audio_data, 'audio/flac')

        self.assertFalse(result['success'])
        self.assertIn('format', result['error'].lower())

    def test_oversized_audio_rejected(self):
        """Rejects audio data over 10MB."""
        huge_audio = base64.b64encode(b'x' * (11 * 1024 * 1024)).decode('utf-8')

        result = self.generator.generate_from_audio(huge_audio, self.media_type)

        self.assertFalse(result['success'])
        self.assertIn('large', result['error'].lower())

    @patch.object(AIInvoiceGenerator, '_call_claude_audio_api')
    def test_line_items_validated(self, mock_api):
        """Line items with negative quantities are cleaned."""
        mock_api.return_value = {
            'client_name': None,
            'line_items': [
                {'description': 'Work', 'quantity': -5, 'unit_price': 100},
                {'description': '', 'quantity': 1, 'unit_price': 50},
            ],
            'transcript': 'Some work.'
        }

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertTrue(result['success'])
        items = result['invoice_data']['line_items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['quantity'], 1)

    @patch.object(AIInvoiceGenerator, '_call_claude_audio_api')
    def test_payment_terms_validated(self, mock_api):
        """Invalid payment_terms are set to null."""
        mock_api.return_value = {
            'payment_terms': 'net_999',
            'line_items': [
                {'description': 'Work', 'quantity': 1, 'unit_price': 100}
            ],
            'transcript': 'Work for $100, net 999.'
        }

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertTrue(result['success'])
        self.assertIsNone(result['invoice_data']['payment_terms'])
