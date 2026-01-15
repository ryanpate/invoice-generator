"""
Commission tracking service for affiliate program.

Handles creating commissions when referred users make purchases.
"""
from decimal import Decimal
from django.db import transaction

from apps.affiliates.models import Referral, Commission


COMMISSION_RATE = Decimal('0.20')  # 20% commission


def create_commission_for_purchase(
    user,
    purchase_type: str,
    purchase_description: str,
    purchase_amount: Decimal,
    stripe_payment_intent_id: str = '',
    stripe_invoice_id: str = ''
) -> Commission | None:
    """
    Create a commission for an affiliate if the user was referred.

    Args:
        user: The user who made the purchase
        purchase_type: Type of purchase ('subscription', 'credit_pack', 'template')
        purchase_description: Description of what was purchased
        purchase_amount: Amount paid in dollars
        stripe_payment_intent_id: Stripe payment intent ID (optional)
        stripe_invoice_id: Stripe invoice ID (optional)

    Returns:
        Commission object if created, None if user wasn't referred
    """
    # Check if user has a referral
    try:
        referral = Referral.objects.select_related('affiliate').get(referred_user=user)
    except Referral.DoesNotExist:
        return None

    # Check if affiliate is still approved
    if referral.affiliate.status != 'approved':
        return None

    # Mark referral as converted if not already
    if not referral.converted:
        referral.mark_converted()

    # Calculate commission
    commission_amount = purchase_amount * COMMISSION_RATE

    # Create commission record
    with transaction.atomic():
        commission = Commission.objects.create(
            affiliate=referral.affiliate,
            referral=referral,
            purchase_type=purchase_type,
            purchase_description=purchase_description,
            purchase_amount=purchase_amount,
            commission_rate=COMMISSION_RATE,
            amount=commission_amount,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_invoice_id=stripe_invoice_id,
            status='pending'
        )

        # Update affiliate stats
        referral.affiliate.update_stats()

    return commission


def get_referral_for_user(user) -> Referral | None:
    """Get the referral record for a user, if any."""
    try:
        return Referral.objects.select_related('affiliate').get(referred_user=user)
    except Referral.DoesNotExist:
        return None
