"""
Signal handlers for companies app.
"""
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from allauth.account.signals import user_signed_up

from .models import TeamMember, TeamInvitation
from .services.team_email import TeamEmailService


def process_pending_invitations(request, user, **kwargs):
    """
    Process pending team invitations when a new user signs up.

    If there are pending invitations for the user's email address,
    automatically accept them and add the user to the team(s).
    """
    # Find all pending (non-expired, not accepted) invitations for this email
    pending_invitations = TeamInvitation.objects.filter(
        email__iexact=user.email,
        accepted=False,
        expires_at__gt=timezone.now()
    ).select_related('company', 'invited_by')

    for invitation in pending_invitations:
        try:
            # Create team membership
            team_member = TeamMember.objects.create(
                company=invitation.company,
                user=user,
                role=invitation.role,
                invited_by=invitation.invited_by,
            )

            # Mark invitation as accepted
            invitation.accepted = True
            invitation.save(update_fields=['accepted'])

            # Send welcome email
            TeamEmailService.send_welcome_to_team(team_member)

        except Exception:
            # If there's an error (e.g., duplicate membership), skip this invitation
            # Log error but don't break signup
            pass


def process_session_invitation(sender, request, user, **kwargs):
    """
    Process invitation from session when a user logs in.

    If there's a pending invitation token in the session (from clicking
    an invitation link), process it after login.
    """
    token = request.session.pop('pending_invitation_token', None)
    if not token:
        return

    try:
        invitation = TeamInvitation.objects.get(
            token=token,
            accepted=False,
            expires_at__gt=timezone.now()
        )

        # Check if user's email matches invitation
        if user.email.lower() != invitation.email.lower():
            # Email doesn't match, can't accept this invitation
            return

        # Check if already a member
        if TeamMember.objects.filter(company=invitation.company, user=user).exists():
            invitation.accepted = True
            invitation.save(update_fields=['accepted'])
            return

        # Create team membership
        team_member = TeamMember.objects.create(
            company=invitation.company,
            user=user,
            role=invitation.role,
            invited_by=invitation.invited_by,
        )

        # Mark invitation as accepted
        invitation.accepted = True
        invitation.save(update_fields=['accepted'])

        # Send welcome email
        TeamEmailService.send_welcome_to_team(team_member)

    except TeamInvitation.DoesNotExist:
        pass
    except Exception:
        # Log error but don't break login
        pass


# Connect signals
user_signed_up.connect(process_pending_invitations)
user_logged_in.connect(process_session_invitation)
