"""
Tests for API v2 AI generation endpoints.

Covers:
- Text generation: valid description, missing description, quota exhausted,
  service error, unauthenticated access.
- Voice generation: valid audio upload, missing audio file, unsupported format,
  quota exhausted, service error, unauthenticated access.

All Anthropic API calls are mocked via unittest.mock.patch so tests run
without network access or a configured ANTHROPIC_API_KEY.
"""
import io
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser


AI_GENERATE_URL = '/api/v2/ai/generate/'
AI_VOICE_GENERATE_URL = '/api/v2/ai/voice-generate/'

SAMPLE_LINE_ITEMS = [
    {'description': 'Web Development', 'quantity': 10.0, 'unit_price': 150.0},
    {'description': 'Bug Fixes', 'quantity': 2.0, 'unit_price': 150.0},
]

SAMPLE_INVOICE_DATA = {
    'client_name': 'Acme Corp',
    'client_email': 'billing@acme.com',
    'client_phone': None,
    'client_address': None,
    'invoice_name': None,
    'payment_terms': 'net_30',
    'currency': 'USD',
    'tax_rate': None,
    'notes': None,
    'line_items': SAMPLE_LINE_ITEMS,
    'transcript': 'Invoice Acme Corp for ten hours web dev at 150 dollars per hour.',
}


def make_user(email='ai_test@example.com', password='testpass123'):
    return CustomUser.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password=password,
    )


def auth_client(user):
    """Return an APIClient with a valid JWT Bearer token for *user*."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


def make_audio_file(content=b'fake-audio-bytes', name='recording.webm',
                    content_type='audio/webm'):
    """Create an in-memory file-like object that mimics an uploaded audio file."""
    f = io.BytesIO(content)
    f.name = name
    f.content_type = content_type
    return f


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

class AIGenerateViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    # -- Happy path ----------------------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_valid_description_returns_line_items(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_line_items.return_value = {
            'success': True,
            'line_items': SAMPLE_LINE_ITEMS,
        }

        response = self.client.post(
            AI_GENERATE_URL,
            {'description': 'Built a React dashboard, 10 hours at $150/hr'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('line_items', data)
        self.assertIn('remaining', data)
        self.assertEqual(len(data['line_items']), 2)
        self.assertEqual(data['line_items'][0]['description'], 'Web Development')
        MockGenerator.assert_called_once_with(self.user)
        instance.generate_line_items.assert_called_once_with(
            'Built a React dashboard, 10 hours at $150/hr'
        )

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_description_is_stripped_before_passing_to_service(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_line_items.return_value = {
            'success': True,
            'line_items': SAMPLE_LINE_ITEMS,
        }

        self.client.post(
            AI_GENERATE_URL,
            {'description': '  Consulting work  '},
            format='json',
        )

        instance.generate_line_items.assert_called_once_with('Consulting work')

    # -- Validation errors ---------------------------------------------------

    def test_missing_description_returns_400(self):
        response = self.client.post(AI_GENERATE_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_empty_description_returns_400(self):
        response = self.client.post(
            AI_GENERATE_URL, {'description': '   '}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    # -- Quota enforcement ---------------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_quota_exhausted_returns_429(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (
            False,
            "You've used all 3 AI generations this month. Upgrade your plan for more.",
        )

        response = self.client.post(
            AI_GENERATE_URL,
            {'description': 'Logo design $500'},
            format='json',
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json())
        # generate_line_items must NOT be called when quota is already exhausted
        instance.generate_line_items.assert_not_called()

    # -- Service / upstream errors -------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_service_error_returns_500(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_line_items.return_value = {
            'success': False,
            'error': 'An error occurred while generating line items. Please try again.',
        }

        response = self.client.post(
            AI_GENERATE_URL,
            {'description': 'Freelance photography session'},
            format='json',
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    # -- Authentication ------------------------------------------------------

    def test_unauthenticated_request_returns_401(self):
        anon_client = APIClient()
        response = anon_client.post(
            AI_GENERATE_URL,
            {'description': 'Design work 5 hours'},
            format='json',
        )
        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Voice generation
# ---------------------------------------------------------------------------

class AIVoiceGenerateViewTests(TestCase):

    def setUp(self):
        self.user = make_user(email='voice_test@example.com')
        self.client = auth_client(self.user)

    # -- Happy path ----------------------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_valid_audio_returns_structured_data(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_from_audio.return_value = {
            'success': True,
            'invoice_data': dict(SAMPLE_INVOICE_DATA),  # copy so pop() is safe
        }

        audio = make_audio_file()
        response = self.client.post(
            AI_VOICE_GENERATE_URL,
            {'audio': audio},
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('line_items', data)
        self.assertIn('fields', data)
        self.assertIn('transcript', data)
        self.assertIn('remaining', data)
        self.assertEqual(len(data['line_items']), 2)
        self.assertEqual(data['fields']['client_name'], 'Acme Corp')
        self.assertEqual(data['fields']['payment_terms'], 'net_30')
        self.assertNotIn('line_items', data['fields'])
        self.assertNotIn('transcript', data['fields'])
        MockGenerator.assert_called_once_with(self.user)

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_audio_is_base64_encoded_before_service_call(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_from_audio.return_value = {
            'success': True,
            'invoice_data': dict(SAMPLE_INVOICE_DATA),
        }

        raw_bytes = b'some-audio-content'
        audio = make_audio_file(content=raw_bytes, content_type='audio/ogg')
        self.client.post(AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart')

        import base64
        expected_b64 = base64.b64encode(raw_bytes).decode('utf-8')
        instance.generate_from_audio.assert_called_once_with(expected_b64, 'audio/ogg')

    # -- Validation errors ---------------------------------------------------

    def test_missing_audio_file_returns_400(self):
        response = self.client.post(AI_VOICE_GENERATE_URL, {}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_unsupported_audio_format_returns_400(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_from_audio.return_value = {
            'success': False,
            'error': 'Unsupported audio format. Supported: audio/mp4, audio/ogg, audio/wav, audio/webm',
        }

        audio = make_audio_file(content_type='audio/flac')
        response = self.client.post(
            AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_audio_too_large_returns_400(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_from_audio.return_value = {
            'success': False,
            'error': 'Audio too large. Keep recordings under 60 seconds.',
        }

        audio = make_audio_file()
        response = self.client.post(
            AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    # -- Quota enforcement ---------------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_quota_exhausted_returns_429(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (
            False,
            "You've used all 3 AI generations this month. Upgrade your plan for more.",
        )

        audio = make_audio_file()
        response = self.client.post(
            AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart'
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json())
        instance.generate_from_audio.assert_not_called()

    # -- Service / upstream errors -------------------------------------------

    @patch('apps.api_v2.views.ai.AIInvoiceGenerator')
    def test_service_error_returns_500(self, MockGenerator):
        instance = MockGenerator.return_value
        instance.can_generate.return_value = (True, None)
        instance.generate_from_audio.return_value = {
            'success': False,
            'error': 'An error occurred while processing your voice recording. Please try again.',
        }

        audio = make_audio_file()
        response = self.client.post(
            AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart'
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    # -- Authentication ------------------------------------------------------

    def test_unauthenticated_request_returns_401(self):
        anon_client = APIClient()
        audio = make_audio_file()
        response = anon_client.post(
            AI_VOICE_GENERATE_URL, {'audio': audio}, format='multipart'
        )
        self.assertIn(response.status_code, [401, 403])
