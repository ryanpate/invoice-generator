"""
Signal handlers for affiliate program.

Handles:
1. Connecting referral cookies to new user signups
2. Creating commissions when referred users make purchases
"""
from django.dispatch import receiver
from django.db import transaction
from allauth.account.signals import user_signed_up

from .models import Referral


@receiver(user_signed_up)
def connect_referral_to_user(request, user, **kwargs):
    """
    When a new user signs up, check for a referral cookie and connect them.
    """
    referral_cookie = request.COOKIES.get('ref')
    if not referral_cookie:
        return

    try:
        # Find the referral by visitor_id
        referral = Referral.objects.get(visitor_id=referral_cookie)

        # Don't allow self-referrals
        if referral.affiliate.user == user:
            return

        # Connect the user to the referral
        referral.referred_user = user
        referral.save(update_fields=['referred_user'])

        # Update affiliate stats
        referral.affiliate.update_stats()

    except (Referral.DoesNotExist, ValueError):
        # Invalid or expired referral cookie, ignore
        pass
