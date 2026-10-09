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


def plan_edit(user, invoice, cur_name, cur_email, new_name, new_email):
    """
    Decide what an edit to the client costs. cur_* are the client before the
    edit (pass them in: a bound form has already changed the instance).

    Returns (uses_quota, quota_client): whether the edit counts as a new
    invoice, and the (name, email) to store as the invoice's quota client.
    """
    old_name = invoice.quota_client_name or cur_name
    old_email = invoice.quota_client_email or cur_email
    tiers = settings.SUBSCRIPTION_TIERS
    limit = tiers.get(user.effective_tier(), tiers['free']).get('invoices_per_month', 0)
    if limit == -1:
        return False, (new_name, new_email or '')
    if is_new_client(old_name, old_email, new_name, new_email):
        return True, (new_name, new_email or '')
    # A correction keeps the anchor, so the next edit is still measured from it.
    return False, (old_name, old_email or new_email or '')
