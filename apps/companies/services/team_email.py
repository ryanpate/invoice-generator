"""
Team invitation email service.
"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse


class TeamEmailService:
    """Service for sending team-related emails."""

    @staticmethod
    def send_invitation(invitation):
        """
        Send invitation email to a potential team member.

        Args:
            invitation: TeamInvitation instance

        Returns:
            dict with 'success' boolean and 'error' message if failed
        """
        try:
            site_url = getattr(settings, 'SITE_URL', 'https://www.invoicekits.com')
            accept_url = f"{site_url}/invitation/{invitation.token}/"

            # Render HTML email
            html_content = render_to_string('emails/team_invitation.html', {
                'invitation': invitation,
                'company': invitation.company,
                'inviter': invitation.invited_by,
                'accept_url': accept_url,
                'role': invitation.get_role_display(),
                'site_url': site_url,
            })

            # Create subject
            subject = f"You've been invited to join {invitation.company.name} on InvoiceKits"

            # Create email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invitation.email],
            )

            # Set HTML content type
            email.content_subtype = 'html'

            # Send email
            email.send(fail_silently=False)

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def send_welcome_to_team(team_member):
        """
        Send welcome email after a user joins a team.

        Args:
            team_member: TeamMember instance

        Returns:
            dict with 'success' boolean and 'error' message if failed
        """
        try:
            site_url = getattr(settings, 'SITE_URL', 'https://www.invoicekits.com')
            dashboard_url = f"{site_url}/dashboard/"

            # Render HTML email
            html_content = render_to_string('emails/team_welcome.html', {
                'team_member': team_member,
                'company': team_member.company,
                'user': team_member.user,
                'role': team_member.get_role_display(),
                'dashboard_url': dashboard_url,
                'site_url': site_url,
            })

            # Create subject
            subject = f"Welcome to {team_member.company.name}!"

            # Create email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[team_member.user.email],
            )

            # Set HTML content type
            email.content_subtype = 'html'

            # Send email
            email.send(fail_silently=False)

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}
