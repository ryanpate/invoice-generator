"""
Magic Link Service for passwordless client authentication.
"""
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import Client, MagicLinkToken, ClientSession


class MagicLinkService:
    """Service for managing magic link authentication."""

    def __init__(self, request=None):
        self.request = request
        self.site_url = getattr(settings, 'SITE_URL', 'https://www.invoicekits.com')

    def get_or_create_client(self, email, name=''):
        """Get or create a client by email."""
        email = email.lower().strip()
        client, created = Client.objects.get_or_create(
            email__iexact=email,
            defaults={
                'email': email,
                'name': name,
            }
        )

        # Update name if provided and client has no name
        if not created and name and not client.name:
            client.name = name
            client.save(update_fields=['name'])

        return client, created

    def check_rate_limit(self, email):
        """Check if email has exceeded magic link rate limit."""
        limit = getattr(settings, 'CLIENT_PORTAL_MAGIC_LINK_RATE_LIMIT', 5)
        one_hour_ago = timezone.now() - timedelta(hours=1)

        recent_count = MagicLinkToken.objects.filter(
            client__email__iexact=email,
            created_at__gte=one_hour_ago
        ).count()

        return recent_count >= limit

    def create_magic_link(self, email, name='', invoice=None):
        """
        Create a magic link token for client authentication.

        Args:
            email: Client email address
            name: Optional client name
            invoice: Optional invoice to link to

        Returns:
            dict with 'success', 'token', 'url', and 'error' if failed
        """
        # Check rate limit
        if self.check_rate_limit(email):
            return {
                'success': False,
                'error': 'Too many access requests. Please try again in an hour.'
            }

        # Get or create client
        client, _ = self.get_or_create_client(email, name)

        # Invalidate any existing unused tokens
        MagicLinkToken.objects.filter(
            client=client,
            used_at__isnull=True
        ).update(
            expires_at=timezone.now()  # Expire immediately
        )

        # Create new token
        token = MagicLinkToken.objects.create(
            client=client,
            invoice=invoice,
        )

        magic_link_url = f"{self.site_url}/portal/auth/{token.token}/"

        return {
            'success': True,
            'token': token,
            'url': magic_link_url,
            'client': client,
        }

    def verify_token(self, token_string):
        """
        Verify a magic link token and create a session.

        Args:
            token_string: The token from the URL

        Returns:
            dict with 'success', 'session', 'client', 'invoice' and 'error' if failed
        """
        try:
            token = MagicLinkToken.objects.get(token=token_string)
        except MagicLinkToken.DoesNotExist:
            return {'success': False, 'error': 'Invalid or expired link'}

        if not token.is_valid:
            return {'success': False, 'error': 'This link has expired'}

        # Mark token as used
        token.mark_used(self.request)

        # Update client last access
        token.client.last_accessed_at = timezone.now()
        token.client.save(update_fields=['last_accessed_at'])

        # Create session
        session = ClientSession.objects.create(
            client=token.client,
            magic_link_token=token,
            ip_address=MagicLinkToken.get_client_ip(self.request) if self.request else None,
            user_agent=(self.request.META.get('HTTP_USER_AGENT', '')[:500]
                       if self.request else ''),
        )

        return {
            'success': True,
            'session': session,
            'client': token.client,
            'invoice': token.invoice,
        }

    def validate_session(self, session_token):
        """
        Validate an existing session token.

        Args:
            session_token: The session token from cookie

        Returns:
            ClientSession if valid, None otherwise
        """
        try:
            session = ClientSession.objects.get(
                session_token=session_token,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            # Refresh session on valid access
            session.refresh()
            return session
        except ClientSession.DoesNotExist:
            return None

    def send_magic_link_email(self, email, name='', invoice=None, custom_message=''):
        """
        Create and send a magic link email to a client.

        Args:
            email: Client email address
            name: Optional client name
            invoice: Optional invoice for context
            custom_message: Optional custom message to include

        Returns:
            dict with 'success' and 'error' if failed
        """
        # Create magic link
        result = self.create_magic_link(email, name, invoice)
        if not result['success']:
            return result

        # Prepare email context
        context = {
            'client': result['client'],
            'magic_link_url': result['url'],
            'invoice': invoice,
            'company': invoice.company if invoice else None,
            'custom_message': custom_message,
            'expiry_minutes': getattr(settings, 'CLIENT_PORTAL_MAGIC_LINK_EXPIRY_MINUTES', 30),
            'site_url': self.site_url,
        }

        # Render email
        html_content = render_to_string('emails/client_magic_link.html', context)

        subject = 'Your InvoiceKits Portal Access Link'
        if invoice:
            subject = f'View Invoice {invoice.invoice_number} from {invoice.company.name}'

        # Send email
        try:
            email_message = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            email_message.content_subtype = 'html'
            email_message.send(fail_silently=False)

            return {'success': True, 'token': result['token']}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def logout(self, session_token):
        """
        Invalidate a client session (logout).
        """
        try:
            session = ClientSession.objects.get(session_token=session_token)
            session.invalidate()
            return {'success': True}
        except ClientSession.DoesNotExist:
            return {'success': False, 'error': 'Session not found'}
