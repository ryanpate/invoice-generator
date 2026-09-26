"""
Abuse limits for the no-login "email me this PDF" endpoints.

Every limit is counted in the database over a rolling 24 hours: the app runs
one gunicorn worker that recycles every ~250 requests, so an in-process cache
would forget counts constantly.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import AnonymousEmailSend

PER_IP_DAILY = 3
PER_RECIPIENT_DAILY = 3
# Backstop for a bot rotating IPs and addresses. Real volume is a handful a day.
SITE_WIDE_DAILY = 30

# A hidden field on both forms. People never see it; form-filling bots do.
HONEYPOT_FIELD = 'website'


def client_ip(request):
    # Railway's edge sets X-Real-IP; REMOTE_ADDR is the proxy.
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')


def is_bot(request):
    return bool(request.POST.get(HONEYPOT_FIELD, '').strip())


def limit_reached(request, recipient):
    recent = AnonymousEmailSend.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    ip = client_ip(request)
    return (
        recent.count() >= SITE_WIDE_DAILY
        or (ip and recent.filter(ip_address=ip).count() >= PER_IP_DAILY)
        or recent.filter(recipient__iexact=recipient).count() >= PER_RECIPIENT_DAILY
    )


def record_send(request, recipient):
    AnonymousEmailSend.objects.create(ip_address=client_ip(request), recipient=recipient)
