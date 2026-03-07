"""
API v2 AI generation endpoints.

Provides text-based and voice-based invoice generation using the Claude API.
Both endpoints enforce the user's plan-based AI generation quota. Quota
tracking and incrementing are delegated entirely to AIInvoiceGenerator so
the service remains the single source of truth.
"""
import base64

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.invoices.services.ai_generator import AIInvoiceGenerator


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_view(request):
    """
    Generate invoice line items from a natural language description.

    Request body (JSON):
        description (str): Plain-English description of the work to invoice.

    Response 200:
        line_items (list): Generated line items with description, quantity,
                           unit_price, and optional notes.
        remaining (int|None): Generations remaining this month, or null for
                              unlimited plans.

    Response 400: Missing or empty description.
    Response 429: Plan quota exhausted.
    Response 500: Upstream Claude API error.
    """
    description = request.data.get('description', '').strip()
    if not description:
        return Response(
            {'error': 'Description is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generator = AIInvoiceGenerator(request.user)

    # Quota check before touching the API so we don't burn a generation slot
    # on a request we know will be refused.
    can_gen, quota_error = generator.can_generate()
    if not can_gen:
        return Response(
            {'error': quota_error},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    result = generator.generate_line_items(description)

    if not result.get('success'):
        return Response(
            {'error': result.get('error', 'Failed to generate line items.')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({
        'line_items': result.get('line_items', []),
        'remaining': request.user.get_ai_generations_remaining(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def ai_voice_generate_view(request):
    """
    Generate structured invoice data from a voice recording.

    Accepts a multipart upload with an audio file. The file is base64-encoded
    and forwarded to the Claude Audio API which transcribes and extracts
    invoice fields in a single call.

    Request body (multipart/form-data):
        audio (file): Audio recording (webm, ogg, mp4, or wav, max 10 MB).

    Response 200:
        line_items (list):  Extracted line items.
        fields (dict):      Other extracted invoice fields (client_name,
                            client_email, payment_terms, currency, etc.).
        transcript (str):   Raw transcript of the recording.
        remaining (int|None): Generations remaining, or null for unlimited.

    Response 400: No audio file provided or unsupported format / size.
    Response 429: Plan quota exhausted.
    Response 500: Upstream Claude API error.
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response(
            {'error': 'Audio file is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generator = AIInvoiceGenerator(request.user)

    can_gen, quota_error = generator.can_generate()
    if not can_gen:
        return Response(
            {'error': quota_error},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Detect the MIME type from the upload; fall back to a common default so
    # the service's ALLOWED_MEDIA_TYPES guard can reject it cleanly.
    media_type = audio_file.content_type or 'audio/webm'

    audio_bytes = audio_file.read()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    result = generator.generate_from_audio(audio_b64, media_type)

    if not result.get('success'):
        error_msg = result.get('error', 'Failed to process voice recording.')
        # Distinguish client-side errors (format/size) from server-side ones.
        if any(kw in error_msg.lower() for kw in ('unsupported', 'invalid', 'too large')):
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    invoice_data = result.get('invoice_data', {})
    line_items = invoice_data.pop('line_items', [])
    transcript = invoice_data.pop('transcript', '')

    return Response({
        'line_items': line_items,
        'fields': invoice_data,
        'transcript': transcript,
        'remaining': request.user.get_ai_generations_remaining(),
    })
