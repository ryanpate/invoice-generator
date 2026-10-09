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
PER_IP_DAILY = 10
# Backstop for a bot rotating IPs. Real volume is a handful a day.
SITE_WIDE_DAILY = 200

LIMIT_ERROR = (
    "You've reached today's limit for free previews. Create a free account "
    "to keep making invoices."
)


def limit_reached(request):
    recent = GuestPdfDownload.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    ip = client_ip(request)
    return (
        recent.count() >= SITE_WIDE_DAILY
        or bool(ip and recent.filter(ip_address=ip).count() >= PER_IP_DAILY)
    )


def record_download(request):
    GuestPdfDownload.objects.create(ip_address=client_ip(request))
