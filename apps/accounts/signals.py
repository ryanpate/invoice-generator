"""
Signal handlers for accounts app.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from allauth.account.signals import user_signed_up


def send_welcome_email(request, user, **kwargs):
    """Send welcome email when a new user signs up."""
    subject = 'Welcome to InvoiceKits!'

    # Render HTML email
    html_message = render_to_string('emails/welcome.html', {
        'user': user,
        'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://www.invoicekits.com',
    })

    # Create plain text version
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,  # Don't break signup if email fails
        )
    except Exception:
        # Log error but don't break signup
        pass


# Connect signal
user_signed_up.connect(send_welcome_email)
