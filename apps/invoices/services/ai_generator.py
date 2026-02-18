"""
AI Invoice Generator Service

Uses Claude to convert natural language work descriptions
into structured invoice line items.
"""
import json
import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class AIInvoiceGenerator:
    """
    Service for generating invoice line items from natural language descriptions.

    Uses Claude API to parse work descriptions and generate structured line items
    with descriptions, quantities, and rates.
    """

    SYSTEM_PROMPT = """You are an invoice line item generator for a professional invoicing application. Your task is to convert natural language work descriptions into structured invoice line items.

OUTPUT FORMAT:
You must output ONLY a valid JSON array of line items. No explanations, no markdown, no code blocks - just the raw JSON array.

Each line item must have these fields:
- description (string): A professional, concise description of the work
- quantity (number): The quantity (hours, units, etc.)
- unit_price (number): The price per unit (hourly rate, unit price, etc.)
- notes (string, optional): Additional context if helpful

GUIDELINES:
1. For hourly work: Use hours as quantity and hourly rate as unit_price
2. For fixed-price work: Use quantity=1 and the fixed price as unit_price
3. Break complex projects into logical, itemized line items
4. Use professional, clear descriptions (not too verbose)
5. If rates aren't specified, use reasonable industry-standard rates
6. Round quantities and prices to 2 decimal places
7. For ambiguous work, infer the most likely interpretation

EXAMPLES:

Input: "Website design 20 hours at $100/hr"
Output: [{"description": "Website Design", "quantity": 20, "unit_price": 100.00}]

Input: "Built React dashboard with 3 charts, 12 hours at $150/hr. Also fixed 2 bugs."
Output: [{"description": "React Dashboard Development", "quantity": 8, "unit_price": 150.00, "notes": "Including 3 data visualization charts"}, {"description": "API Integration & Data Binding", "quantity": 4, "unit_price": 150.00}, {"description": "Bug Fixes", "quantity": 2, "unit_price": 150.00}]

Input: "Logo design $500, business cards $200"
Output: [{"description": "Logo Design", "quantity": 1, "unit_price": 500.00}, {"description": "Business Card Design", "quantity": 1, "unit_price": 200.00}]

Input: "5 hours consulting, 3 hours project management"
Output: [{"description": "Consulting Services", "quantity": 5, "unit_price": 150.00}, {"description": "Project Management", "quantity": 3, "unit_price": 125.00}]

REMEMBER: Output ONLY the JSON array, nothing else."""

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

    ALLOWED_MEDIA_TYPES = {'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/wav'}
    VALID_PAYMENT_TERMS = {'due_on_receipt', 'net_15', 'net_30', 'net_60', 'net_90'}
    VALID_CURRENCIES = {'USD', 'EUR', 'GBP', 'CAD', 'AUD'}
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, user):
        """
        Initialize the AI generator for a specific user.

        Args:
            user: The CustomUser instance making the request
        """
        self.user = user
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')

    def can_generate(self) -> tuple[bool, Optional[str]]:
        """
        Check if the user can use the AI generator.

        Returns:
            tuple: (can_generate: bool, error_message: Optional[str])
        """
        if not self.api_key:
            return False, "AI generation is not configured. Please contact support."

        if not self.user.can_use_ai_generator():
            remaining = self.user.get_ai_generations_remaining()
            limit = self.user.get_ai_generation_limit()
            if limit is not None:
                return False, f"You've used all {limit} AI generations this month. Upgrade your plan for more."
            return False, "You've reached your AI generation limit this month."

        return True, None

    def generate_line_items(self, description: str) -> dict:
        """
        Generate invoice line items from a natural language description.

        Args:
            description: Natural language description of work to invoice

        Returns:
            dict: {
                'success': bool,
                'line_items': list[dict] (if success),
                'error': str (if not success)
            }
        """
        # Check if user can generate
        can_gen, error = self.can_generate()
        if not can_gen:
            return {'success': False, 'error': error}

        # Validate description
        description = description.strip()
        if not description:
            return {'success': False, 'error': 'Please provide a work description.'}

        if len(description) < 10:
            return {'success': False, 'error': 'Please provide a more detailed description (at least 10 characters).'}

        if len(description) > 5000:
            return {'success': False, 'error': 'Description is too long. Please keep it under 5000 characters.'}

        try:
            # Call Claude API
            line_items = self._call_claude_api(description)

            if not line_items:
                return {'success': False, 'error': 'Failed to generate line items. Please try with a different description.'}

            # Validate and clean line items
            cleaned_items = self._validate_line_items(line_items)

            if not cleaned_items:
                return {'success': False, 'error': 'Generated line items were invalid. Please try again.'}

            # Increment usage counter
            self.user.increment_ai_generation()

            return {'success': True, 'line_items': cleaned_items}

        except Exception as e:
            logger.exception(f"Error generating AI line items: {e}")
            return {'success': False, 'error': 'An error occurred while generating line items. Please try again.'}

    def _call_claude_api(self, description: str) -> Optional[list]:
        """
        Call the Claude API to generate line items.

        Args:
            description: The work description to convert

        Returns:
            list: The parsed line items, or None on error
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate invoice line items for the following work:\n\n{description}"
                    }
                ]
            )

            # Extract text content from response
            response_text = message.content[0].text.strip()

            # Parse JSON response
            return self._parse_response(response_text)

        except anthropic.APIConnectionError:
            logger.error("Failed to connect to Anthropic API")
            return None
        except anthropic.RateLimitError:
            logger.error("Anthropic API rate limit exceeded")
            return None
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error: {e.status_code} - {e.message}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error calling Claude API: {e}")
            return None

    def _parse_response(self, response_text: str) -> Optional[list]:
        """
        Parse the JSON response from Claude.

        Args:
            response_text: The raw text response from Claude

        Returns:
            list: Parsed line items, or None on error
        """
        try:
            # Try to parse as JSON directly
            data = json.loads(response_text)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'line_items' in data:
                return data['line_items']
            else:
                logger.warning(f"Unexpected response structure: {type(data)}")
                return None

        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find a raw array
            array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group(0))
                except json.JSONDecodeError:
                    pass

            logger.warning(f"Failed to parse response: {response_text[:200]}")
            return None

    def _validate_line_items(self, line_items: list) -> list:
        """
        Validate and clean the generated line items.

        Args:
            line_items: Raw line items from Claude

        Returns:
            list: Cleaned and validated line items
        """
        if not isinstance(line_items, list):
            return []

        cleaned = []
        for item in line_items:
            if not isinstance(item, dict):
                continue

            # Extract and validate required fields
            description = item.get('description', '').strip()
            if not description:
                continue

            try:
                quantity = float(item.get('quantity', 1))
                if quantity <= 0:
                    quantity = 1
                # Round to 2 decimal places
                quantity = round(quantity, 2)
            except (TypeError, ValueError):
                quantity = 1

            try:
                unit_price = float(item.get('unit_price', 0))
                if unit_price < 0:
                    unit_price = 0
                # Round to 2 decimal places
                unit_price = round(unit_price, 2)
            except (TypeError, ValueError):
                unit_price = 0

            # Create cleaned item
            cleaned_item = {
                'description': description[:500],  # Limit description length
                'quantity': quantity,
                'unit_price': unit_price,
            }

            # Add optional notes if present
            notes = item.get('notes', '').strip()
            if notes:
                cleaned_item['notes'] = notes[:500]

            cleaned.append(cleaned_item)

        return cleaned

    def generate_from_audio(self, audio_data: str, media_type: str) -> dict:
        """
        Generate structured invoice data from an audio recording.

        Sends audio to Claude Audio API for transcription and invoice field
        extraction in a single API call.

        Args:
            audio_data: Base64-encoded audio data
            media_type: MIME type of the audio (e.g. 'audio/webm')

        Returns:
            dict: {
                'success': bool,
                'invoice_data': dict (if success),
                'error': str (if not success)
            }
        """
        if media_type not in self.ALLOWED_MEDIA_TYPES:
            return {
                'success': False,
                'error': f'Unsupported audio format. Supported: {", ".join(sorted(self.ALLOWED_MEDIA_TYPES))}'
            }

        import base64 as b64
        try:
            raw_bytes = b64.b64decode(audio_data)
        except Exception:
            return {'success': False, 'error': 'Invalid audio data.'}

        if len(raw_bytes) > self.MAX_AUDIO_SIZE:
            return {'success': False, 'error': 'Audio too large. Keep recordings under 60 seconds.'}

        parsed = self._call_claude_audio_api(audio_data, media_type)

        if parsed is None:
            return {
                'success': False,
                'error': 'An error occurred while processing your voice recording. Please try again.'
            }

        line_items = parsed.get('line_items', [])
        if not isinstance(line_items, list):
            line_items = []

        cleaned_items = self._validate_line_items(line_items)
        if not cleaned_items:
            return {
                'success': False,
                'error': "Couldn't extract any invoice items from the recording. Try speaking more clearly about the work you did and the amounts."
            }

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
        Call the Claude API with audio input for transcription and extraction.

        Args:
            audio_data: Base64-encoded audio data
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
        """
        Parse a JSON response from Claude, expecting a dict (object).

        Tries direct parsing first, then code-block extraction, then brace matching.

        Args:
            response_text: The raw text response from Claude

        Returns:
            dict: Parsed response, or None on error
        """
        import re

        # Try direct JSON parse
        try:
            result = json.loads(response_text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # Try finding raw JSON object
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
        """
        Clean and truncate a string value.

        Args:
            value: The value to clean (may be None or non-string)
            max_length: Maximum allowed length

        Returns:
            str or None: Cleaned string, or None if empty/invalid
        """
        if value is None or not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned[:max_length] if cleaned else None

    @staticmethod
    def _clean_number(value, min_val=None, max_val=None):
        """
        Clean and validate a numeric value.

        Args:
            value: The value to clean (may be None or non-numeric)
            min_val: Minimum allowed value (inclusive), or None
            max_val: Maximum allowed value (inclusive), or None

        Returns:
            float or None: Cleaned number, or None if invalid/out of range
        """
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
