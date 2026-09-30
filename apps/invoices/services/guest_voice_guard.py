"""
Abuse limits for guest (no-login) voice invoicing.

Each use sends up to 10 MB of audio to Claude on our bill. The old cap was one
per session cookie, which a bot resets by dropping the cookie, so uses are
counted in the database over a rolling 24 hours.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import GuestVoiceGeneration
from .anon_email_guard import client_ip

# Above the one-per-session cap so people behind a shared IP are not locked out.
PER_IP_DAILY = 3
# Backstop for a bot rotating IPs.
SITE_WIDE_DAILY = 50


def limit_reached(request):
    recent = GuestVoiceGeneration.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    ip = client_ip(request)
    return (
        recent.count() >= SITE_WIDE_DAILY
        or bool(ip and recent.filter(ip_address=ip).count() >= PER_IP_DAILY)
    )


def record_use(request):
    GuestVoiceGeneration.objects.create(ip_address=client_ip(request))
