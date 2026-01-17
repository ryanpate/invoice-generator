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
