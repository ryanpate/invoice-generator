"""
Abuse limits for no-login PDF downloads (/try/ and the past-due notice tool).

Downloads had no limit at all, so a script could generate any number of
invoices without an account. Counted in the database over a rolling 24 hours,
like the other guest guards, because a bot drops its session cookie.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import GuestPdfDownload
from .anon_email_guard import client_ip

# Room for a person fixing typos and re-downloading, or a shared office IP.
# No site-wide cap, unlike the email guard: one bot could spend it and shut
# /try/ for every real visitor. A download sends nothing from our domain, and
# scam content is refused by scam_guard regardless of volume.
PER_IP_DAILY = 10

LIMIT_ERROR = (
    "You've reached today's limit for free previews. Create a free account "
    "to keep making invoices."
)


def limit_reached(request):
    ip = client_ip(request)
    return bool(ip) and GuestPdfDownload.objects.filter(
        ip_address=ip, created_at__gte=timezone.now() - timedelta(hours=24)
    ).count() >= PER_IP_DAILY


def record_download(request):
    GuestPdfDownload.objects.create(ip_address=client_ip(request))
