"""
Billing views for API v2.

Covers:
- usage_view       GET  /api/v2/billing/usage/
- entitlements_view GET /api/v2/billing/entitlements/
- verify_apple_receipt POST /api/v2/billing/apple/verify-receipt/
- register_device  POST /api/v2/billing/device/register/
- apple_server_notification POST /api/v2/billing/apple/notifications/  (AllowAny)
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.api_v2.models import DeviceToken

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Apple product ID → subscription tier mapping
# ---------------------------------------------------------------------------

APPLE_PRODUCT_TIER_MAP = {
    'com.invoicekits.starter.monthly': 'starter',
    'com.invoicekits.professional.monthly': 'professional',
    'com.invoicekits.business.monthly': 'business',
    'com.invoicekits.starter.annual': 'starter',
    'com.invoicekits.professional.annual': 'professional',
    'com.invoicekits.business.annual': 'business',
}


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_view(request):
    """
    GET /api/v2/billing/usage/

    Returns current usage statistics for the authenticated user.
    """
    user = request.user
    user.check_usage_reset()

    tier_config = settings.SUBSCRIPTION_TIERS.get(user.subscription_tier, {})
    invoice_limit = tier_config.get('invoices_per_month', 0)
    api_limit = tier_config.get('api_calls_per_month', 0)
    # AI_GENERATION_LIMITS uses None to mean "unlimited"
    raw_ai_limit = getattr(settings, 'AI_GENERATION_LIMITS', {}).get(user.subscription_tier, 0)
    ai_unlimited = raw_ai_limit is None or raw_ai_limit == -1
    ai_limit = None if ai_unlimited else raw_ai_limit

    # Invoice quota: -1 means unlimited in SUBSCRIPTION_TIERS
    invoice_unlimited = invoice_limit == -1
    api_unlimited = api_limit == -1

    # Subscribers show monthly usage; credit users show credit balance
    if user.is_active_subscriber():
        invoice_usage = {
            'used': user.invoices_created_this_month,
            'limit': None if invoice_unlimited else invoice_limit,
            'unlimited': invoice_unlimited,
            'percentage': user.get_usage_percentage(),
        }
    else:
        total_credits = user.get_available_credits()
        invoice_usage = {
            'credits_balance': user.credits_balance,
            'free_credits_remaining': user.free_credits_remaining,
            'total_credits': total_credits,
            'total_credits_purchased': user.total_credits_purchased,
        }

    data = {
        'subscription_tier': user.subscription_tier,
        'subscription_status': user.subscription_status,
        'payment_source': user.payment_source,
        'invoices': invoice_usage,
        'api_calls': {
            'used': user.api_calls_this_month,
            'limit': None if api_unlimited else api_limit,
            'unlimited': api_unlimited,
        },
        'ai_generations': {
            'used': user.ai_generations_used,
            'limit': ai_limit,
            'unlimited': ai_unlimited,
            'remaining': (
                max(0, ai_limit - user.ai_generations_used)
                if not ai_unlimited and ai_limit is not None
                else None
            ),
        },
    }
    return Response(data)


# ---------------------------------------------------------------------------
# Entitlements
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def entitlements_view(request):
    """
    GET /api/v2/billing/entitlements/

    Returns a flat map of feature flags for the authenticated user.
    The mobile app uses this to gate UI features without local business logic.
    """
    user = request.user
    tier_config = settings.SUBSCRIPTION_TIERS.get(user.subscription_tier, {})

    data = {
        'subscription_tier': user.subscription_tier,
        'is_active_subscriber': user.is_active_subscriber(),
        'features': {
            'batch_upload': user.has_batch_upload(),
            'api_access': user.has_api_access(),
            'recurring_invoices': user.has_recurring_invoices(),
            'team_seats': user.has_team_seats(),
            'time_tracking': user.has_time_tracking() if hasattr(user, 'has_time_tracking') else False,
            'ai_invoice_generator': user.can_use_ai_generator() if hasattr(user, 'can_use_ai_generator') else False,
            'shows_watermark': user.shows_watermark(),
        },
        'available_templates': user.get_available_templates(),
        'recurring_invoice_limit': user.get_recurring_invoice_limit(),
        'team_seat_limit': user.get_team_seat_limit(),
        'max_active_timers': user.get_max_active_timers() if hasattr(user, 'get_max_active_timers') else 0,
    }
    return Response(data)


# ---------------------------------------------------------------------------
# Apple In-App Purchase receipt verification
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_apple_receipt(request):
    """
    POST /api/v2/billing/apple/verify-receipt/

    Accepts a signed transaction from StoreKit 2 (transaction_jws string).
    Updates the user's subscription tier and marks payment_source as 'apple'.

    Body:
      {
        "transaction_jws": "<StoreKit2 JWS string>",
        "product_id": "com.invoicekits.professional.monthly"
      }

    TODO: Implement full Apple App Store Server API verification:
      1. Send transaction_jws to https://api.storekit.itunes.apple.com/inApps/v1/transactions/{transactionId}
         (or decode the JWS locally using Apple's public keys from https://appleid.apple.com/auth/keys)
      2. Verify the bundle ID matches your app
      3. Verify the transaction is not expired (use expiresDate for subscriptions)
      4. Map the productIdentifier to a subscription tier
      5. Use the originalTransactionId to detect renewals and cancellations
      6. Handle Apple Server Notifications V2 for real-time status updates
    """
    user = request.user
    transaction_jws = request.data.get('transaction_jws')
    product_id = request.data.get('product_id')

    if not transaction_jws or not product_id:
        return Response(
            {'error': 'Both transaction_jws and product_id are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Map product ID to tier
    tier = APPLE_PRODUCT_TIER_MAP.get(product_id)
    if not tier:
        return Response(
            {'error': f'Unknown product_id: {product_id}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # TODO: Replace stub with real Apple App Store Server API verification.
    # For now, trust the client-supplied product_id after basic validation.
    logger.warning(
        'Apple receipt verification is stubbed. '
        'Granting tier=%s to user=%s based on product_id=%s without server-side validation.',
        tier,
        user.email,
        product_id,
    )

    user.subscription_tier = tier
    user.subscription_status = 'active'
    user.payment_source = 'apple'
    user.save(update_fields=['subscription_tier', 'subscription_status', 'payment_source'])

    return Response(
        {
            'subscription_tier': user.subscription_tier,
            'subscription_status': user.subscription_status,
            'payment_source': user.payment_source,
            'product_id': product_id,
            'warning': (
                'Receipt verification is not yet implemented server-side. '
                'Tier granted based on client-supplied product_id.'
            ),
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Device token registration
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_device(request):
    """
    POST /api/v2/billing/device/register/

    Creates or updates a DeviceToken for push notifications.

    Body:
      {
        "token": "<APNs or FCM device token>",
        "platform": "ios"  | "android"
      }
    """
    token_value = request.data.get('token')
    platform = request.data.get('platform', 'ios')

    if not token_value:
        return Response(
            {'error': 'token is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if platform not in ('ios', 'android'):
        return Response(
            {'error': 'platform must be "ios" or "android".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    device_token, created = DeviceToken.objects.update_or_create(
        user=request.user,
        token=token_value,
        defaults={
            'platform': platform,
            'is_active': True,
        },
    )

    return Response(
        {
            'id': device_token.id,
            'token': device_token.token,
            'platform': device_token.platform,
            'is_active': device_token.is_active,
            'created': created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Apple Server Notifications V2 (webhook)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def apple_server_notification(request):
    """
    POST /api/v2/billing/apple/notifications/

    Receives Apple App Store Server Notifications V2.
    This endpoint must be registered in App Store Connect under
    "App Store Server Notifications" with the Production and Sandbox URLs.

    The payload is a signed JWS (signedPayload) containing a JSON notification.

    TODO: Implement full handling:
      1. Decode and verify the signedPayload JWS using Apple's public keys
      2. Parse the notificationType (SUBSCRIBED, DID_RENEW, EXPIRED, etc.)
      3. Extract the originalTransactionId and look up the user
      4. Update user.subscription_status and user.subscription_tier accordingly
      5. Return HTTP 200 so Apple stops retrying

    Reference:
      https://developer.apple.com/documentation/appstoreservernotifications
    """
    signed_payload = request.data.get('signedPayload')

    if not signed_payload:
        return Response(
            {'error': 'signedPayload is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.info(
        'Received Apple Server Notification (stub). '
        'signedPayload length=%d. Full verification not yet implemented.',
        len(signed_payload),
    )

    # TODO: decode, verify, and process the notification.
    # Acknowledge receipt immediately so Apple does not retry.
    return Response(status=status.HTTP_200_OK)
