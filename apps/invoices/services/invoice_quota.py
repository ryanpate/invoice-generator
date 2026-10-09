"""
Metered plans count invoices, so editing an invoice to bill a different client
is a new invoice. Without this a free account could rewrite one invoice for a
new recipient, download or email it, and repeat forever.
"""
from difflib import SequenceMatcher

from django.conf import settings

# At or above this a name edit is a correction ("Jon Smith" -> "John Smith").
SAME_NAME_RATIO = 0.8

LIMIT_ERROR = (
    'Changing the client makes this a new invoice, and you have reached your '
    'invoice limit for this month. Please upgrade your plan or create the '
    'invoice next month.'
)


def _norm(value):
    return (value or '').strip().casefold()


def is_new_client(old_name, old_email, new_name, new_email):
    old_email, new_email = _norm(old_email), _norm(new_email)
    if old_email and new_email != old_email:
        return True
    return SequenceMatcher(None, _norm(old_name), _norm(new_name)).ratio() < SAME_NAME_RATIO


def retarget_uses_quota(user, old_name, old_email, new_name, new_email):
    """True when this edit counts as a new invoice against the user's monthly quota."""
    tiers = settings.SUBSCRIPTION_TIERS
    limit = tiers.get(user.effective_tier(), tiers['free']).get('invoices_per_month', 0)
    return limit != -1 and is_new_client(old_name, old_email, new_name, new_email)
