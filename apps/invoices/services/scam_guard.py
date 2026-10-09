"""
Refuse to generate invoices that match known payment-scam patterns.

The common invoice scam ("callback phishing") is a fake renewal or purchase
invoice from a big brand -- Geek Squad, Norton, PayPal -- with a phone number
to call "if you did not authorize this charge". The phone call is the scam.
Two signals, each narrow enough that a real small business does not trip it:

  1. The sender's business name *is* a commonly impersonated brand
     ("PayPal", "Norton LifeLock" -- but not "Norton Electric").
  2. Any text pairs a phone number with dispute/cancel/refund language.
"""
import logging
import re

logger = logging.getLogger(__name__)

_BRANDS = (
    r'geek\s*squad|norton(\s*life\s*lock)?|life\s*lock|mc\s*afee|pay\s*pal|best\s*buy|'
    r'coin\s*base|binance|microsoft|windows\s*defender|apple|apple\s*care|itunes|'
    r'amazon|venmo|cash\s*app|zelle|meta\s*mask|trust\s*wallet|avast|kaspersky|'
    r'malwarebytes|total\s*av|webroot|ebay|netflix|irs'
)
_SUFFIXES = (
    r'inc|llc|ltd|corp|corporation|co|support|billing|services?|team|security|'
    r'protection|total\s*protection|antivirus|help\s*desk|customer\s*care|payments?|'
    r'online|store|subscriptions?|renewals?|department|dept'
)
IMPERSONATED_SENDER = re.compile(
    rf'^\W*({_BRANDS})(\W+({_SUFFIXES}))*\W*$', re.IGNORECASE
)

# 10+ digits with the usual separators: +1 (888) 555-0100, 1-888-555-0100, ...
# No newlines, so digits from separate fields never join into a "number".
PHONE = re.compile(r'\+?\d[\d \t().\-]{8,}\d')
# The lines that tell a victim to phone in. Ordinary invoice wording ("domain
# renewal", "no refunds after 30 days") does not match.
CALLBACK_LANGUAGE = re.compile(
    r'unauthori[sz]ed|not\s+authori[sz]ed|'
    r'did\s*n[o\']?t\s+(authori[sz]e|make|recogni[sz]e|order|place|request)|'
    r'(cancel|refund|dispute)\w*\s+(this|the|your)\s+'
    r'(order|purchase|subscription|renewal|charge|transaction|payment)|'
    r'(charge|transaction|payment)\s+(dispute|reversal)',
    re.IGNORECASE,
)

ERROR = (
    "We can't generate this invoice: it matches a pattern used in payment scams "
    "(a well-known brand as the sender, or a phone number to call to cancel or "
    "dispute a charge). If this is a mistake, email support@invoicekits.com."
)


def looks_like_scam(sender_name, texts):
    """sender_name is the business issuing the invoice; texts is every other field."""
    if sender_name and IMPERSONATED_SENDER.match(sender_name.strip()):
        return True
    combined = '\n'.join(t for t in [sender_name, *texts] if t)
    return bool(PHONE.search(combined) and CALLBACK_LANGUAGE.search(combined))


def log_block(request, where, sender_name):
    from .anon_email_guard import client_ip

    logger.warning(
        'Blocked scam-pattern invoice at %s: sender=%r ip=%s user=%s',
        where, sender_name, client_ip(request),
        getattr(request.user, 'pk', None),
    )
