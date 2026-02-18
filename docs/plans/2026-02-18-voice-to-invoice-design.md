# Voice-to-Invoice Design

**Date:** 2026-02-18
**Status:** Approved
**Approach:** Browser MediaRecorder → Claude Audio API (single call transcription + parsing)

## Overview

Add voice input to the invoice create/edit pages and /try/ page. Users speak their invoice details into their microphone, Claude transcribes and parses the audio into structured invoice data, and the form fields are populated automatically. One API call handles both transcription and field extraction. No new dependencies.

## Architecture & Data Flow

```
User clicks mic button
    → Browser requests microphone permission
    → MediaRecorder captures audio (WebM)
    → User clicks "Stop & Generate"
    → Audio blob → base64 encoded in JS
    → POST /invoices/ai-voice-generate/
      { "audio_data": "<base64>", "media_type": "audio/webm" }
    → Django view:
        1. Validates user can use AI (same quota check)
        2. Decodes base64 audio
        3. Calls Claude API with audio content block + system prompt
        4. Claude returns structured JSON with all invoice fields
        5. Increments AI usage counter
        6. Returns JSON response
    → Frontend JS:
        1. Shows transcript and list of fields filled
        2. User clicks "Apply to Invoice"
        3. Populates all form fields + line items
        4. User reviews and edits before saving
```

Audio is never stored. Processed in memory and discarded after the API call.

## Files Changed

| File | Change |
|------|--------|
| `apps/invoices/services/ai_generator.py` | Add `generate_from_audio()` method, `VOICE_SYSTEM_PROMPT` |
| `apps/invoices/views.py` | Add `ai_voice_generate` endpoint |
| `apps/invoices/urls.py` | Add URL route |
| `templates/invoices/create.html` | Add mic button + recording UI in AI Generate section |
| `templates/invoices/edit.html` | Same |
| `templates/invoices/try.html` | Same, with guest cap logic |

## Backend

### Claude Audio API Call

New method on `AIInvoiceGenerator`:

```python
def generate_from_audio(self, audio_data: bytes, media_type: str) -> dict:
    """
    Send audio to Claude, get structured invoice data back.
    Single API call — Claude transcribes + parses simultaneously.
    """
```

Message structure:

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    system=VOICE_SYSTEM_PROMPT,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "audio",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_audio
                }
            },
            {
                "type": "text",
                "text": "Parse this voice recording into invoice data."
            }
        ]
    }]
)
```

### Voice System Prompt

```
You are an invoice data extractor. Listen to the audio and extract
structured invoice data. Return ONLY valid JSON with this schema:

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
    {
      "description": "string",
      "quantity": number,
      "unit_price": number
    }
  ],
  "transcript": "string"
}

Rules:
- Extract whatever fields are mentioned. Set unmentioned fields to null.
- Map payment terms: "net 30" → "net_30", "due on receipt" → "due_on_receipt", etc.
- Map currency: "dollars" → "USD", "euros" → "EUR", etc.
- line_items is required — must have at least one item.
- Include the raw transcript so the user can see what was heard.
```

### Response Schema

```json
{
  "success": true,
  "invoice_data": {
    "client_name": "John Smith",
    "client_email": null,
    "client_address": "123 Main St, Austin TX",
    "payment_terms": "net_30",
    "currency": "USD",
    "tax_rate": null,
    "notes": null,
    "line_items": [
      {"description": "Logo design", "quantity": 1, "unit_price": 500.00},
      {"description": "Brand guidelines", "quantity": 1, "unit_price": 300.00}
    ],
    "transcript": "Invoice John Smith at 123 Main St Austin Texas..."
  },
  "remaining": 7,
  "is_unlimited": false
}
```

### Validation

- Audio size capped at 10MB (reject before API call)
- `media_type` must be: `audio/webm`, `audio/ogg`, `audio/mp4`, `audio/wav`
- Response JSON validated — line_items must be non-empty
- Field values cleaned same as existing `_validate_line_items()`

### Guest Usage (/try/ page)

- Session-based counter: `request.session['voice_generations_used']`
- Cap: 1 free voice generation per session
- After cap: "Sign up free to keep using voice invoicing."

```python
if request.user.is_authenticated:
    if not user.can_use_ai_generator():
        return JsonResponse({'success': False, 'error': '...'})
else:
    used = request.session.get('voice_generations_used', 0)
    if used >= 1:
        return JsonResponse({'success': False, 'error': 'Sign up free...'})
    request.session['voice_generations_used'] = used + 1
```

## Frontend

### UI States

| State | What's shown |
|-------|-------------|
| Idle | Textarea + "Voice" mic button side by side |
| Recording | Red pulsing dot, live timer (00:00), "Stop & Generate" button. Textarea hidden. |
| Processing | Spinner + "Listening and parsing your invoice..." |
| Result | Transcript ("Heard: ..."), list of fields filled, "Apply to Invoice" / "Try Again" |
| Error | Red banner with message |

### Recording Constraints

- Max recording: 60 seconds (auto-stop, warning at 55s)
- Min recording: 1 second (client-side reject)
- Max file size: 10MB (client-side reject)

### Form Population Rules

- Only empty fields get populated — existing values not overwritten
- "Apply to Invoice" is an explicit user action, no auto-population
- Line items added via existing `addLineItemToForm()` function
- Totals recalculated after items added

### Browser Compatibility

- MediaRecorder: Chrome, Firefox, Safari 14.5+, Edge (~95% of users)
- Unsupported browsers: mic button hidden entirely, textarea-only experience
- Feature detection: check `navigator.mediaDevices` and `MediaRecorder`

## Error Handling

### Microphone Permissions

| Scenario | Message |
|----------|---------|
| Denied | "Microphone access is needed for voice input. You can still type above." |
| Previously blocked | "Microphone is blocked. Click the lock icon in your address bar to enable it." |

### Recording Errors

| Scenario | Message |
|----------|---------|
| Too short (<1s) | "Recording too short. Hold the mic for at least a few seconds." |
| Too long (>60s) | Auto-stop at 60s. Warning at 55s. |
| Too large (>10MB) | "Recording too long. Try a shorter description." |
| Navigate away while recording | `beforeunload` warning. Stream released on unload. |

### API Errors

| Scenario | Message |
|----------|---------|
| Timeout (30s) | "Voice processing took too long. Try again or type instead." |
| API error (500, rate limit) | "Voice processing temporarily unavailable. Type your description instead." |
| Invalid JSON from Claude | Retry parse once, then return error. |
| No line items extracted | "Couldn't extract invoice items. Try speaking more clearly about the work and amounts." |
| Network error | "Connection lost. Recording wasn't sent. Please try again." |

### Quota

| Scenario | Behavior |
|----------|----------|
| At limit | Mic button disabled + tooltip |
| "Try Again" | Resets UI, does NOT consume a generation |
| /try/ guest at cap | Mic disabled + signup CTA |

## Usage Limits

Same as existing AI text generation:

| Tier | Monthly Limit |
|------|--------------|
| Free | 3 |
| Starter | 10 |
| Professional | Unlimited |
| Business | Unlimited |
| /try/ guest | 1 per session |

## Testing Strategy

| Layer | Scope | Method |
|-------|-------|--------|
| Unit — AI service | `generate_from_audio()` returns valid JSON, handles errors, validates schema, rejects oversized audio | Mock Anthropic client |
| Unit — View | Auth check, quota, session cap, size limit, media_type validation | Django test client with mock AI service |
| Integration | POST audio → parsed invoice data | Mock only Anthropic API |
| Frontend | Recording, timer, UI states, form population, error messages | Manual browser testing (Chrome, Firefox, Safari) |
| Browser compat | MediaRecorder availability, graceful fallback | Feature detection test |

## New Dependencies

None. Uses existing `anthropic` package and browser-native `MediaRecorder` API.
