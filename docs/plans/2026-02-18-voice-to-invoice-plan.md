# Voice-to-Invoice Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add voice dictation to invoice create/edit and /try/ pages so users can speak invoice details and have Claude parse audio into structured form data in a single API call.

**Architecture:** Browser MediaRecorder captures WebM audio → base64 POST to Django → Claude Audio API transcribes + extracts all invoice fields as JSON → frontend populates form. No new dependencies.

**Tech Stack:** Django, Anthropic Python SDK (existing), browser MediaRecorder API, vanilla JavaScript.

**Design doc:** `docs/plans/2026-02-18-voice-to-invoice-design.md`

---

### Task 1: Backend — Add `generate_from_audio()` to AIInvoiceGenerator

**Files:**
- Modify: `apps/invoices/services/ai_generator.py:17-287` (add VOICE_SYSTEM_PROMPT constant and `generate_from_audio()` method)
- Create: `apps/invoices/tests/__init__.py`
- Create: `apps/invoices/tests/test_ai_generator_voice.py`

**Step 1: Create test directory and write failing tests**

Create `apps/invoices/tests/__init__.py` (empty file).

Create `apps/invoices/tests/test_ai_generator_voice.py`:

```python
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
        # Minimal valid audio bytes (doesn't matter — we mock the API)
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
                {'description': '', 'quantity': 1, 'unit_price': 50},  # empty desc — dropped
            ],
            'transcript': 'Some work.'
        }

        result = self.generator.generate_from_audio(self.audio_data, self.media_type)

        self.assertTrue(result['success'])
        items = result['invoice_data']['line_items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['quantity'], 1)  # negative → 1

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
```

**Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.invoices.tests.test_ai_generator_voice -v 2`

Expected: FAIL — `generate_from_audio` method doesn't exist, `_call_claude_audio_api` doesn't exist.

**Step 3: Implement `generate_from_audio()` and `_call_claude_audio_api()`**

Add to `apps/invoices/services/ai_generator.py` after line 24 (after existing SYSTEM_PROMPT), add `VOICE_SYSTEM_PROMPT`:

```python
    VOICE_SYSTEM_PROMPT = """You are an invoice data extractor. Listen to the audio and extract structured invoice data. Return ONLY valid JSON — no explanations, no markdown, no code blocks.

OUTPUT SCHEMA:
{
  "client_name": "string or null",
  "client_email": "string or null",
  "client_phone": "string or null",
  "client_address": "string or null",
  "invoice_name": "string or null",
  "payment_terms": "due_on_receipt|net_15|net_30|net_60|net_90 or null",
  "currency": "USD|EUR|GBP|CAD|AUD or null",
  "tax_rate": "number or null",
  "notes": "string or null",
  "line_items": [
    {"description": "string", "quantity": number, "unit_price": number}
  ],
  "transcript": "string"
}

RULES:
- Extract whatever fields are mentioned. Set unmentioned fields to null.
- Map payment terms naturally: "net 30" → "net_30", "due on receipt" → "due_on_receipt"
- Map currency naturally: "dollars" → "USD", "euros" → "EUR", "pounds" → "GBP"
- line_items is required — must contain at least one item.
- Include the raw transcript of what you heard."""
```

Add `ALLOWED_MEDIA_TYPES` and `VALID_PAYMENT_TERMS` after the prompts:

```python
    ALLOWED_MEDIA_TYPES = {'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/wav'}
    VALID_PAYMENT_TERMS = {'due_on_receipt', 'net_15', 'net_30', 'net_60', 'net_90'}
    VALID_CURRENCIES = {'USD', 'EUR', 'GBP', 'CAD', 'AUD'}
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB in bytes (before base64)
```

Add `generate_from_audio()` method after the existing `generate_line_items()` method (after line ~140):

```python
    def generate_from_audio(self, audio_data: str, media_type: str) -> dict:
        """
        Generate full invoice data from audio input.

        Args:
            audio_data: Base64-encoded audio string
            media_type: MIME type of the audio (e.g., 'audio/webm')

        Returns:
            dict with 'success', 'invoice_data' or 'error'
        """
        # Validate media type
        if media_type not in self.ALLOWED_MEDIA_TYPES:
            return {
                'success': False,
                'error': f'Unsupported audio format. Supported: {", ".join(sorted(self.ALLOWED_MEDIA_TYPES))}'
            }

        # Validate size (base64 is ~4/3 the size of raw bytes)
        import base64 as b64
        try:
            raw_bytes = b64.b64decode(audio_data)
        except Exception:
            return {'success': False, 'error': 'Invalid audio data.'}

        if len(raw_bytes) > self.MAX_AUDIO_SIZE:
            return {'success': False, 'error': 'Audio too large. Keep recordings under 60 seconds.'}

        # Call Claude with audio
        parsed = self._call_claude_audio_api(audio_data, media_type)

        if parsed is None:
            return {
                'success': False,
                'error': 'An error occurred while processing your voice recording. Please try again.'
            }

        # Validate line items exist
        line_items = parsed.get('line_items', [])
        if not isinstance(line_items, list):
            line_items = []

        cleaned_items = self._validate_line_items(line_items)
        if not cleaned_items:
            return {
                'success': False,
                'error': "Couldn't extract any invoice items from the recording. Try speaking more clearly about the work you did and the amounts."
            }

        # Clean and validate all fields
        invoice_data = {
            'client_name': self._clean_string(parsed.get('client_name'), 200),
            'client_email': self._clean_string(parsed.get('client_email'), 254),
            'client_phone': self._clean_string(parsed.get('client_phone'), 30),
            'client_address': self._clean_string(parsed.get('client_address'), 500),
            'invoice_name': self._clean_string(parsed.get('invoice_name'), 200),
            'payment_terms': parsed.get('payment_terms') if parsed.get('payment_terms') in self.VALID_PAYMENT_TERMS else None,
            'currency': parsed.get('currency') if parsed.get('currency') in self.VALID_CURRENCIES else None,
            'tax_rate': self._clean_number(parsed.get('tax_rate'), min_val=0, max_val=100),
            'notes': self._clean_string(parsed.get('notes'), 1000),
            'line_items': cleaned_items,
            'transcript': self._clean_string(parsed.get('transcript'), 2000) or '',
        }

        return {'success': True, 'invoice_data': invoice_data}

    def _call_claude_audio_api(self, audio_data: str, media_type: str):
        """
        Call Claude API with audio content block.

        Args:
            audio_data: Base64-encoded audio string
            media_type: MIME type of the audio

        Returns:
            dict: Parsed JSON response, or None on error
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=self.VOICE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "audio",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": audio_data,
                            }
                        },
                        {
                            "type": "text",
                            "text": "Parse this voice recording into invoice data."
                        }
                    ]
                }]
            )

            response_text = message.content[0].text.strip()
            return self._parse_response_as_dict(response_text)

        except anthropic.APIConnectionError:
            logger.error("Failed to connect to Anthropic API for voice generation")
            return None
        except anthropic.RateLimitError:
            logger.error("Anthropic API rate limit exceeded for voice generation")
            return None
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error for voice generation: {e.status_code} - {e.message}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error calling Claude Audio API: {e}")
            return None

    def _parse_response_as_dict(self, response_text: str):
        """Parse Claude response as a JSON dict (not array like line items)."""
        # Try direct parse
        try:
            result = json.loads(response_text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } block
        brace_match = re.search(r'\{[\s\S]*\}', response_text)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse voice generation response as JSON dict: {response_text[:200]}")
        return None

    @staticmethod
    def _clean_string(value, max_length):
        """Return cleaned string or None."""
        if value is None or not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned[:max_length] if cleaned else None

    @staticmethod
    def _clean_number(value, min_val=None, max_val=None):
        """Return cleaned number or None."""
        if value is None:
            return None
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return None
            if max_val is not None and num > max_val:
                return None
            return round(num, 2)
        except (TypeError, ValueError):
            return None
```

**Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.invoices.tests.test_ai_generator_voice -v 2`

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add apps/invoices/services/ai_generator.py apps/invoices/tests/
git commit -m "feat: add voice-to-invoice AI generation service

Add generate_from_audio() method to AIInvoiceGenerator that sends audio
to Claude Audio API for transcription + invoice field extraction in a
single API call. Includes validation for media types, audio size, and
all extracted invoice fields."
```

---

### Task 2: Backend — Add `ai_voice_generate` Django view

**Files:**
- Modify: `apps/invoices/views.py:1402-1442` (add new view after existing `ai_generate_line_items`)
- Modify: `apps/invoices/urls.py:31` (add URL route after ai-generate)
- Create: `apps/invoices/tests/test_voice_view.py`

**Step 1: Write failing tests**

Create `apps/invoices/tests/test_voice_view.py`:

```python
"""Tests for the ai_voice_generate view."""
import base64
import json
from unittest.mock import patch

from django.test import TestCase, RequestFactory
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

    def test_requires_auth_or_session(self):
        """Unauthenticated request without session works (guest mode for /try/)."""
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
```

**Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.invoices.tests.test_voice_view -v 2`

Expected: FAIL — URL `invoices:ai_voice_generate` not found.

**Step 3: Implement the view and URL**

Add to `apps/invoices/urls.py` after line 31 (after the existing ai-generate path):

```python
    path('ai-voice-generate/', views.ai_voice_generate, name='ai_voice_generate'),
```

Add to `apps/invoices/views.py` after the existing `ai_generate_line_items` function (after line 1442):

```python
def ai_voice_generate(request):
    """
    AJAX endpoint to generate full invoice data from voice audio.

    Accepts a POST with base64 audio data. Works for both authenticated
    users (quota-based) and guests (session-based cap of 1).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'AJAX required'}, status=400)

    import json as json_mod
    try:
        data = json_mod.loads(request.body)
    except json_mod.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

    audio_data = data.get('audio_data', '')
    media_type = data.get('media_type', '')

    if not audio_data:
        return JsonResponse({'success': False, 'error': 'No audio data provided.'})

    if not media_type:
        return JsonResponse({'success': False, 'error': 'No media type provided.'})

    # Quota check: authenticated user or guest session
    if request.user.is_authenticated:
        if not request.user.can_use_ai_generator():
            remaining = request.user.get_ai_generations_remaining()
            limit = request.user.get_ai_generation_limit()
            return JsonResponse({
                'success': False,
                'error': f"You've used all {limit} AI generations this month. Upgrade your plan for more."
            })
    else:
        used = request.session.get('voice_generations_used', 0)
        if used >= 1:
            return JsonResponse({
                'success': False,
                'error': 'Sign up free to keep using voice invoicing.'
            })

    # Generate invoice data from audio
    from .services.ai_generator import AIInvoiceGenerator

    user = request.user if request.user.is_authenticated else None
    generator = AIInvoiceGenerator(user)
    result = generator.generate_from_audio(audio_data, media_type)

    if result['success']:
        # Increment usage
        if request.user.is_authenticated:
            request.user.increment_ai_generation()
            remaining = request.user.get_ai_generations_remaining()
            result['remaining'] = remaining
            result['is_unlimited'] = remaining is None
        else:
            request.session['voice_generations_used'] = request.session.get('voice_generations_used', 0) + 1
            result['remaining'] = 0
            result['is_unlimited'] = False

    return JsonResponse(result)
```

**Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.invoices.tests.test_voice_view -v 2`

Expected: All 6 tests PASS.

**Step 5: Run all tests to check for regressions**

Run: `python manage.py test apps.invoices.tests -v 2`

Expected: All 13 tests PASS (7 from Task 1 + 6 from Task 2).

**Step 6: Commit**

```bash
git add apps/invoices/views.py apps/invoices/urls.py apps/invoices/tests/test_voice_view.py
git commit -m "feat: add ai_voice_generate endpoint for voice-to-invoice

New AJAX endpoint at /invoices/ai-voice-generate/ that accepts base64
audio, sends to Claude Audio API, returns structured invoice data.
Supports both authenticated users (quota) and guests (1/session cap)."
```

---

### Task 3: Frontend — Add voice recording UI to create.html

**Files:**
- Modify: `templates/invoices/create.html:94-161` (AI Generate section HTML)
- Modify: `templates/invoices/create.html:490-691` (JavaScript section)

**Step 1: Add mic button and recording UI to the AI Generate HTML section**

In `templates/invoices/create.html`, modify the AI Generate section. After the existing textarea (line 131) and before the Generate button (line 134), add the voice button. Replace the content inside `<div id="ai-content">` (lines 125-160) with:

```html
                    <div id="ai-content" class="hidden">
                        <p class="text-sm text-purple-700 dark:text-purple-300 mb-4">
                            Describe your work in plain English or use your voice — AI will generate invoice fields for you.
                        </p>

                        <!-- Text input + Voice button row -->
                        <div class="flex gap-3 mb-4">
                            <div class="flex-1" id="ai-text-input">
                                <textarea id="ai-description" rows="3" placeholder="Example: Built a React dashboard with 3 charts, 12 hours at $150/hr. Also fixed 2 bugs." class="w-full rounded-lg border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-purple-500 focus:border-purple-500 placeholder-gray-400 dark:placeholder-gray-500"></textarea>
                            </div>
                            <div id="voice-btn-container" class="flex-shrink-0 hidden">
                                <button type="button" id="ai-voice-btn" class="h-full px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow-md flex flex-col items-center justify-center gap-1" title="Record voice invoice">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-14 0m14 0a7 7 0 00-14 0m14 0v1a7 7 0 01-14 0v-1m14 0H5m7 7v4m-4 0h8"/>
                                    </svg>
                                    <span class="text-xs">Voice</span>
                                </button>
                            </div>
                        </div>

                        <!-- Recording UI (hidden until recording starts) -->
                        <div id="voice-recording-ui" class="hidden mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center gap-3">
                                    <span class="flex h-3 w-3">
                                        <span class="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-red-400 opacity-75"></span>
                                        <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                                    </span>
                                    <span class="text-red-700 dark:text-red-300 font-medium">Recording...</span>
                                    <span id="voice-timer" class="text-red-600 dark:text-red-400 font-mono text-lg">00:00</span>
                                </div>
                                <button type="button" id="voice-stop-btn" class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors">
                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                                    Stop & Generate
                                </button>
                            </div>
                            <p id="voice-warning" class="hidden mt-2 text-sm text-red-500 dark:text-red-400"></p>
                        </div>

                        <!-- Voice Processing UI -->
                        <div id="voice-processing-ui" class="hidden mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
                            <div class="flex items-center gap-3">
                                <svg class="w-5 h-5 animate-spin text-purple-600" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span class="text-purple-700 dark:text-purple-300 font-medium">Listening and parsing your invoice...</span>
                            </div>
                        </div>

                        <!-- Voice Result UI -->
                        <div id="voice-result-ui" class="hidden mb-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700">
                            <div class="mb-3">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                    </svg>
                                    <span class="text-sm font-medium text-green-800 dark:text-green-200">Heard:</span>
                                </div>
                                <p id="voice-transcript" class="text-sm text-green-700 dark:text-green-300 italic ml-6"></p>
                            </div>
                            <div class="mb-3">
                                <p id="voice-fields-filled" class="text-sm text-green-700 dark:text-green-300 ml-6"></p>
                            </div>
                            <div class="flex gap-3 ml-6">
                                <button type="button" id="voice-apply-btn" class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors text-sm">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                    Apply to Invoice
                                </button>
                                <button type="button" id="voice-retry-btn" class="inline-flex items-center gap-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 text-sm font-medium transition-colors">
                                    Try Again
                                </button>
                            </div>
                        </div>

                        <button type="button" id="ai-generate-btn" class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow-md">
                            <svg id="ai-generate-icon" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                            </svg>
                            <span id="ai-generate-text">Generate Line Items</span>
                        </button>

                        <!-- AI Generated Preview (existing — keep as-is) -->
                        <div id="ai-preview" class="hidden mt-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-purple-200 dark:border-purple-700">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="font-medium text-gray-900 dark:text-white">Generated Line Items</h3>
                                <button type="button" id="ai-add-all" class="inline-flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                                    </svg>
                                    Add All to Invoice
                                </button>
                            </div>
                            <div id="ai-items-list" class="space-y-2"></div>
                        </div>

                        <!-- Error Message -->
                        <div id="ai-error" class="hidden mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg text-sm">
                        </div>
                    </div>
```

**Step 2: Add voice recording JavaScript**

In the `<script>` section of `create.html`, after line 691 (after the existing `addLineItemToForm` function) but before the closing `});` on line 692, add the voice recording JavaScript:

```javascript
    // ==========================================
    // Voice Recording for AI Invoice Generation
    // ==========================================

    const voiceBtnContainer = document.getElementById('voice-btn-container');
    const voiceBtn = document.getElementById('ai-voice-btn');
    const voiceRecordingUI = document.getElementById('voice-recording-ui');
    const voiceProcessingUI = document.getElementById('voice-processing-ui');
    const voiceResultUI = document.getElementById('voice-result-ui');
    const voiceStopBtn = document.getElementById('voice-stop-btn');
    const voiceTimer = document.getElementById('voice-timer');
    const voiceWarning = document.getElementById('voice-warning');
    const voiceTranscript = document.getElementById('voice-transcript');
    const voiceFieldsFilled = document.getElementById('voice-fields-filled');
    const voiceApplyBtn = document.getElementById('voice-apply-btn');
    const voiceRetryBtn = document.getElementById('voice-retry-btn');

    let mediaRecorder = null;
    let audioChunks = [];
    let recordingStream = null;
    let timerInterval = null;
    let recordingSeconds = 0;
    let voiceInvoiceData = null;

    // Feature detection: show voice button only if supported
    if (navigator.mediaDevices && typeof MediaRecorder !== 'undefined') {
        voiceBtnContainer.classList.remove('hidden');
    }

    function resetVoiceUI() {
        voiceRecordingUI.classList.add('hidden');
        voiceProcessingUI.classList.add('hidden');
        voiceResultUI.classList.add('hidden');
        voiceWarning.classList.add('hidden');
        document.getElementById('ai-text-input').classList.remove('hidden');
        voiceBtn.disabled = false;
        voiceInvoiceData = null;
        stopTimer();
    }

    function startTimer() {
        recordingSeconds = 0;
        voiceTimer.textContent = '00:00';
        timerInterval = setInterval(() => {
            recordingSeconds++;
            const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
            const secs = String(recordingSeconds % 60).padStart(2, '0');
            voiceTimer.textContent = `${mins}:${secs}`;

            // Warning at 55 seconds
            if (recordingSeconds === 55) {
                voiceWarning.textContent = 'Wrapping up in 5 seconds...';
                voiceWarning.classList.remove('hidden');
            }

            // Auto-stop at 60 seconds
            if (recordingSeconds >= 60) {
                stopRecording();
            }
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function releaseStream() {
        if (recordingStream) {
            recordingStream.getTracks().forEach(t => t.stop());
            recordingStream = null;
        }
    }

    // Start recording
    if (voiceBtn) {
        voiceBtn.addEventListener('click', async () => {
            try {
                recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err) {
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    showAiError('Microphone access is needed for voice input. You can still type your description above.');
                } else {
                    showAiError('Could not access microphone. Please check your browser settings.');
                }
                return;
            }

            audioChunks = [];
            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
                           : MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4'
                           : '';

            if (!mimeType) {
                showAiError('Your browser does not support audio recording. Please type your description instead.');
                releaseStream();
                return;
            }

            mediaRecorder = new MediaRecorder(recordingStream, { mimeType });
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };
            mediaRecorder.onstop = handleRecordingComplete;
            mediaRecorder.start(100); // Collect data every 100ms

            // Show recording UI, hide text input
            document.getElementById('ai-text-input').classList.add('hidden');
            voiceRecordingUI.classList.remove('hidden');
            hideAiError();
            startTimer();
        });
    }

    // Stop recording
    if (voiceStopBtn) {
        voiceStopBtn.addEventListener('click', stopRecording);
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
    }

    async function handleRecordingComplete() {
        stopTimer();
        releaseStream();

        // Check minimum recording length
        if (recordingSeconds < 1) {
            resetVoiceUI();
            showAiError('Recording too short. Hold the mic for at least a few seconds.');
            return;
        }

        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunks, { type: mimeType });

        // Check file size (10MB limit)
        if (blob.size > 10 * 1024 * 1024) {
            resetVoiceUI();
            showAiError('Recording too long. Try a shorter description.');
            return;
        }

        // Show processing state
        voiceRecordingUI.classList.add('hidden');
        voiceProcessingUI.classList.remove('hidden');

        // Convert to base64
        const base64 = await blobToBase64(blob);

        try {
            const response = await fetch('{% url "invoices:ai_voice_generate" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    audio_data: base64,
                    media_type: mimeType
                })
            });

            const data = await response.json();

            voiceProcessingUI.classList.add('hidden');

            if (data.success) {
                voiceInvoiceData = data.invoice_data;
                showVoiceResult(data);
                if (data.remaining !== undefined) {
                    updateAiRemaining(data.remaining, data.is_unlimited);
                }
            } else {
                resetVoiceUI();
                showAiError(data.error || 'Failed to process voice recording.');
            }
        } catch (error) {
            console.error('Voice generation error:', error);
            resetVoiceUI();
            showAiError('Connection lost. Your recording wasn\'t sent. Please try again.');
        }
    }

    function blobToBase64(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                // Remove the data:audio/webm;base64, prefix
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.readAsDataURL(blob);
        });
    }

    function showVoiceResult(data) {
        const inv = data.invoice_data;

        // Show transcript
        voiceTranscript.textContent = inv.transcript || '(no transcript available)';

        // Count filled fields
        const filled = [];
        if (inv.client_name) filled.push('client name');
        if (inv.client_email) filled.push('email');
        if (inv.client_address) filled.push('address');
        if (inv.payment_terms) filled.push('payment terms');
        if (inv.currency) filled.push('currency');
        if (inv.tax_rate !== null && inv.tax_rate !== undefined) filled.push('tax rate');
        if (inv.notes) filled.push('notes');
        if (inv.invoice_name) filled.push('invoice name');
        const itemCount = (inv.line_items || []).length;
        if (itemCount > 0) filled.push(`${itemCount} line item${itemCount > 1 ? 's' : ''}`);

        voiceFieldsFilled.textContent = `Filled: ${filled.join(', ')}`;

        voiceResultUI.classList.remove('hidden');
    }

    // Apply voice result to form
    if (voiceApplyBtn) {
        voiceApplyBtn.addEventListener('click', () => {
            if (!voiceInvoiceData) return;

            const d = voiceInvoiceData;

            // Populate simple fields (only if currently empty)
            const fieldMap = {
                'id_client_name': d.client_name,
                'id_client_email': d.client_email,
                'id_client_phone': d.client_phone,
                'id_client_address': d.client_address,
                'id_invoice_name': d.invoice_name,
                'id_notes': d.notes,
            };

            for (const [fieldId, value] of Object.entries(fieldMap)) {
                if (value) {
                    const el = document.getElementById(fieldId);
                    if (el && !el.value.trim()) {
                        el.value = value;
                    }
                }
            }

            // Populate dropdowns (only if at default/empty)
            if (d.payment_terms) {
                const ptEl = document.getElementById('id_payment_terms');
                if (ptEl) ptEl.value = d.payment_terms;
            }
            if (d.currency) {
                const curEl = document.getElementById('id_currency');
                if (curEl) curEl.value = d.currency;
            }
            if (d.tax_rate !== null && d.tax_rate !== undefined) {
                const taxEl = document.getElementById('id_tax_rate');
                if (taxEl && (!taxEl.value || parseFloat(taxEl.value) === 0)) {
                    taxEl.value = d.tax_rate;
                }
            }

            // Add line items using existing function
            if (d.line_items && d.line_items.length > 0) {
                d.line_items.forEach(item => addLineItemToForm(item));
            }

            // Recalculate totals
            calculateTotals();

            // Reset voice UI
            resetVoiceUI();

            // Collapse AI section
            aiContent.classList.add('hidden');
            aiChevron.classList.remove('rotate-90');
        });
    }

    // Try Again button
    if (voiceRetryBtn) {
        voiceRetryBtn.addEventListener('click', resetVoiceUI);
    }

    // Warn before leaving during recording
    window.addEventListener('beforeunload', (e) => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            e.preventDefault();
            e.returnValue = 'Recording in progress — leave anyway?';
        }
    });
```

**Step 3: Manually test in browser**

Open `/invoices/create/` in Chrome:
1. Verify mic button appears next to textarea
2. Click mic → browser prompts for microphone permission
3. Speak "Invoice John Smith, $500 for logo design, net 30"
4. Click "Stop & Generate" → processing spinner
5. See transcript + "Filled: client name, 1 line item, payment terms"
6. Click "Apply to Invoice" → form fields populated
7. Verify "Try Again" resets UI without consuming generation

**Step 4: Commit**

```bash
git add templates/invoices/create.html
git commit -m "feat: add voice recording UI to invoice create page

Mic button in AI Generate section records audio via MediaRecorder,
sends to voice endpoint, shows transcript and filled fields preview,
then populates form on 'Apply to Invoice' click. 60s max, auto-stop,
browser feature detection for graceful fallback."
```

---

### Task 4: Frontend — Add voice recording UI to edit.html

**Files:**
- Modify: `templates/invoices/edit.html` (mirror the same AI Generate section and JS from create.html)

**Step 1: Apply the same HTML and JavaScript changes from Task 3 to edit.html**

The edit template has the same AI Generate section structure. Apply identical changes:
1. Same HTML additions inside `<div id="ai-content">` (mic button, recording UI, processing UI, result UI)
2. Same JavaScript additions (voice recording logic, all event handlers)

The only difference: the edit page URL for voice generation is the same (`{% url "invoices:ai_voice_generate" %}`), and the `addLineItemToForm` function already exists in edit.html.

**Step 2: Manually test in browser**

Open an existing invoice's edit page. Verify:
1. Mic button appears
2. Recording + stop + generate works
3. "Apply to Invoice" populates only empty fields (doesn't overwrite existing values)

**Step 3: Commit**

```bash
git add templates/invoices/edit.html
git commit -m "feat: add voice recording UI to invoice edit page

Mirror the same voice recording UI from create.html to the edit page.
Same behavior: mic button, recording, processing, result preview, and
form population with empty-field-only override."
```

---

### Task 5: Frontend — Add voice input to /try/ page

**Files:**
- Modify: `templates/invoices/try.html:97-129` (add AI voice section before line items)
- Modify: `templates/invoices/try.html:224-331` (add voice JS)

**Step 1: Add voice-only AI section to try.html**

The /try/ page doesn't have the AI Generate section at all. Add a simplified voice-only section (no textarea, no text-based AI generation) above the Line Items section (before line 97).

Insert before the Line Items section:

```html
                <!-- Voice Invoice Generator (guest-limited) -->
                <div id="voice-section" class="hidden bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl shadow-sm p-6 transition-colors duration-200 border border-blue-100 dark:border-blue-800">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-lg font-semibold text-blue-900 dark:text-blue-100 flex items-center gap-2">
                            <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-14 0m14 0a7 7 0 00-14 0m14 0v1a7 7 0 01-14 0v-1m14 0H5m7 7v4m-4 0h8"/>
                            </svg>
                            Voice Invoice
                            <span class="px-2 py-0.5 text-xs font-medium bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded-full">New</span>
                        </h2>
                    </div>
                    <p class="text-sm text-blue-700 dark:text-blue-300 mb-4">
                        Speak your invoice details and we'll fill the form for you.
                    </p>

                    <button type="button" id="try-voice-btn" class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow-md">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-14 0m14 0a7 7 0 00-14 0m14 0v1a7 7 0 01-14 0v-1m14 0H5m7 7v4m-4 0h8"/>
                        </svg>
                        Record Invoice Details
                    </button>

                    <!-- Recording / Processing / Result UIs — same structure as create.html -->
                    <div id="try-recording-ui" class="hidden mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <span class="flex h-3 w-3">
                                    <span class="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-red-400 opacity-75"></span>
                                    <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                                </span>
                                <span class="text-red-700 dark:text-red-300 font-medium">Recording...</span>
                                <span id="try-voice-timer" class="text-red-600 dark:text-red-400 font-mono text-lg">00:00</span>
                            </div>
                            <button type="button" id="try-voice-stop" class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors">
                                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                                Stop & Generate
                            </button>
                        </div>
                        <p id="try-voice-warning" class="hidden mt-2 text-sm text-red-500 dark:text-red-400"></p>
                    </div>

                    <div id="try-processing-ui" class="hidden mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
                        <div class="flex items-center gap-3">
                            <svg class="w-5 h-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span class="text-blue-700 dark:text-blue-300 font-medium">Listening and parsing your invoice...</span>
                        </div>
                    </div>

                    <div id="try-result-ui" class="hidden mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700">
                        <div class="mb-3">
                            <span class="text-sm font-medium text-green-800 dark:text-green-200">Heard:</span>
                            <p id="try-transcript" class="text-sm text-green-700 dark:text-green-300 italic mt-1"></p>
                        </div>
                        <p id="try-fields-filled" class="text-sm text-green-700 dark:text-green-300 mb-3"></p>
                        <div class="flex gap-3">
                            <button type="button" id="try-apply-btn" class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors text-sm">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                </svg>
                                Apply to Invoice
                            </button>
                            <button type="button" id="try-retry-btn" class="text-gray-600 dark:text-gray-400 hover:text-gray-800 text-sm font-medium">
                                Try Again
                            </button>
                        </div>
                    </div>

                    <div id="try-voice-error" class="hidden mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg text-sm"></div>
                </div>
```

**Step 2: Add voice JavaScript to try.html**

Add voice recording JS in the existing `<script>` block, adapting it for the /try/ page's form structure. The /try/ page uses `name="item_description_0"` style inputs (not Django formsets), so the "Apply to Invoice" logic creates line items differently — use the existing `add-line-item` button logic.

The voice endpoint URL must be hardcoded since `/try/` doesn't have `{% url %}` access to the invoices namespace. Use `/invoices/ai-voice-generate/` directly.

Form field IDs on /try/ page use `id_<fieldname>` from Django form rendering (e.g., `id_client_name`, `id_payment_terms`, `id_currency`, `id_tax_rate`).

For line items, populate the first empty row or create new rows using the same DOM manipulation as the existing "Add Line Item" button.

**Step 3: Manually test on /try/ page**

1. Visit `/try/` (not logged in)
2. Voice section visible
3. Record and generate — form populates
4. Second attempt — "Sign up free to keep using voice invoicing"
5. Verify the signup CTA is visible

**Step 4: Commit**

```bash
git add templates/invoices/try.html
git commit -m "feat: add voice invoice input to /try/ page

Simplified voice-only section for public try page. Guest-capped at 1
voice generation per session with signup CTA after cap."
```

---

### Task 6: Final integration test and cleanup

**Files:**
- All files from Tasks 1-5

**Step 1: Run all backend tests**

Run: `python manage.py test apps.invoices.tests -v 2`

Expected: All tests PASS.

**Step 2: Run full test suite for regressions**

Run: `python manage.py test -v 2`

Expected: No regressions.

**Step 3: Manual end-to-end test checklist**

Test these scenarios in browser:

- [ ] **create.html** — mic button visible in Chrome, record + stop + generate + apply works
- [ ] **create.html** — "Try Again" resets without consuming generation
- [ ] **create.html** — quota exhausted → mic button disabled
- [ ] **edit.html** — same flow, existing field values not overwritten
- [ ] **try.html** — first voice generation works
- [ ] **try.html** — second attempt shows signup CTA
- [ ] **Firefox** — mic button visible, recording works
- [ ] **Safari** — mic button visible (if 14.5+), recording works
- [ ] **Unsupported browser** — mic button hidden, no errors in console
- [ ] **Mic permission denied** — helpful error message shown
- [ ] **Dark mode** — all voice UI states look correct

**Step 4: Commit any fixes from testing**

```bash
git add -A
git commit -m "fix: address issues found during voice-to-invoice integration testing"
```

**Step 5: Final commit — update CLAUDE.md**

Add voice-to-invoice feature to the Working Features list and Recent Fixes section in CLAUDE.md.

```bash
git add CLAUDE.md
git commit -m "docs: add voice-to-invoice feature to project status"
```
