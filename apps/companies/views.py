"""
Views for companies app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView, TemplateView, View
from django.views.generic.edit import FormView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import Company, TeamMember, TeamInvitation
from .forms import CompanyForm, TeamInviteForm, PaymentReminderSettingsForm
from apps.invoices.models import PaymentReminderSettings


class CompanySettingsView(LoginRequiredMixin, UpdateView):
    """Edit company settings."""
    model = Company
    form_class = CompanyForm
    template_name = 'settings/company.html'
    success_url = reverse_lazy('companies:settings')

    def get_object(self, queryset=None):
        """Get or create company for current user."""
        company, created = Company.objects.get_or_create(
            user=self.request.user,
            defaults={'name': f"{self.request.user.username}'s Company"}
        )
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = settings.INVOICE_TEMPLATES
        context['available_templates'] = self.request.user.get_available_templates()
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Company settings saved successfully!')
        return super().form_valid(form)


@login_required
def remove_logo(request):
    """Remove company logo."""
    if request.method == 'POST':
        try:
            company = request.user.company
            if company.logo:
                company.logo.delete()
                company.save()
                messages.success(request, 'Logo removed successfully.')
        except Company.DoesNotExist:
            pass

    return redirect('companies:settings')


@login_required
def remove_signature(request):
    """Remove company signature."""
    if request.method == 'POST':
        try:
            company = request.user.company
            if company.signature:
                company.signature.delete()
                company.save()
                messages.success(request, 'Signature removed successfully.')
        except Company.DoesNotExist:
            pass

    return redirect('companies:settings')


class TeamRequiredMixin(LoginRequiredMixin):
    """Mixin that requires user to have team seats feature."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_team_seats():
            messages.error(
                request,
                'Team seats are only available on the Business plan. '
                'Please upgrade to access this feature.'
            )
            return redirect('billing:plans')
        return super().dispatch(request, *args, **kwargs)


class TeamAdminRequiredMixin(TeamRequiredMixin):
    """Mixin that requires user to be a team admin."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if result.status_code != 200 or not hasattr(result, 'context_data'):
            # Check admin status
            company = request.user.get_company()
            if company and not company.is_admin(request.user):
                messages.error(request, 'Only team admins can perform this action.')
                return redirect('companies:team')
        return result


class TeamManagementView(TeamRequiredMixin, TemplateView):
    """Display team members and pending invitations."""
    template_name = 'settings/team.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.user.get_company()

        if company:
            context['company'] = company
            context['team_members'] = company.team_members.select_related('user', 'invited_by').all()
            context['pending_invitations'] = company.pending_invitations.filter(
                accepted=False,
                expires_at__gt=timezone.now()
            ).select_related('invited_by')
            context['seat_limit'] = self.request.user.get_team_seat_limit()
            context['seats_used'] = company.get_total_seat_usage()
            context['is_admin'] = company.is_admin(self.request.user)
            context['form'] = TeamInviteForm()

        return context


class InviteTeamMemberView(TeamRequiredMixin, View):
    """Send invitation email to new team member."""

    def post(self, request, *args, **kwargs):
        company = request.user.get_company()
        if not company:
            messages.error(request, 'No company found.')
            return redirect('companies:team')

        if not company.is_admin(request.user):
            messages.error(request, 'Only team admins can invite members.')
            return redirect('companies:team')

        form = TeamInviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            role = form.cleaned_data['role']

            # Check if already a member
            if TeamMember.objects.filter(company=company, user__email__iexact=email).exists():
                messages.error(request, f'{email} is already a team member.')
                return redirect('companies:team')

            # Check if invitation already exists
            existing_invite = TeamInvitation.objects.filter(
                company=company,
                email__iexact=email,
                accepted=False,
                expires_at__gt=timezone.now()
            ).first()
            if existing_invite:
                messages.warning(request, f'An invitation is already pending for {email}.')
                return redirect('companies:team')

            # Check seat limit
            if not company.can_add_team_member():
                messages.error(request, 'Team seat limit reached. Please remove a member or upgrade your plan.')
                return redirect('companies:team')

            # Create invitation
            invitation = TeamInvitation.objects.create(
                company=company,
                email=email,
                role=role,
                invited_by=request.user
            )

            # Send invitation email
            from .services.team_email import TeamEmailService
            TeamEmailService.send_invitation(invitation)

            messages.success(request, f'Invitation sent to {email}.')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])

        return redirect('companies:team')


class AcceptInvitationView(View):
    """Accept invitation via token (can be accessed by unauthenticated users)."""

    def get(self, request, token, *args, **kwargs):
        invitation = get_object_or_404(
            TeamInvitation,
            token=token,
            accepted=False
        )

        if invitation.is_expired:
            messages.error(request, 'This invitation has expired.')
            return redirect('account_login')

        # Store invitation token in session for processing after login/signup
        request.session['pending_invitation_token'] = str(token)

        if request.user.is_authenticated:
            # If logged in, process immediately
            return self._process_invitation(request, invitation)

        # If not logged in, redirect to signup with invitation context
        messages.info(
            request,
            f'You have been invited to join {invitation.company.name}. '
            'Please sign up or log in to accept the invitation.'
        )
        return redirect('account_signup')

    def _process_invitation(self, request, invitation):
        """Process the invitation for an authenticated user."""
        # Check if user's email matches invitation
        if request.user.email.lower() != invitation.email.lower():
            messages.error(
                request,
                f'This invitation was sent to {invitation.email}. '
                f'Please log in with that email address.'
            )
            return redirect('account_login')

        # Check if already a member
        if TeamMember.objects.filter(company=invitation.company, user=request.user).exists():
            messages.info(request, 'You are already a member of this team.')
            invitation.accepted = True
            invitation.save()
            return redirect('accounts:dashboard')

        # Create team membership
        TeamMember.objects.create(
            company=invitation.company,
            user=request.user,
            role=invitation.role,
            invited_by=invitation.invited_by
        )

        # Mark invitation as accepted
        invitation.accepted = True
        invitation.save()

        # Clear session
        if 'pending_invitation_token' in request.session:
            del request.session['pending_invitation_token']

        # Send welcome email
        from .services.team_email import TeamEmailService
        team_member = TeamMember.objects.get(company=invitation.company, user=request.user)
        TeamEmailService.send_welcome_to_team(team_member)

        messages.success(request, f'Welcome to {invitation.company.name}!')
        return redirect('accounts:dashboard')


class RemoveTeamMemberView(TeamRequiredMixin, View):
    """Remove a team member (admin only)."""

    def post(self, request, pk, *args, **kwargs):
        company = request.user.get_company()
        if not company:
            messages.error(request, 'No company found.')
            return redirect('companies:team')

        if not company.is_admin(request.user):
            messages.error(request, 'Only team admins can remove members.')
            return redirect('companies:team')

        member = get_object_or_404(TeamMember, pk=pk, company=company)

        # Cannot remove the owner
        if member.user == company.get_effective_owner():
            messages.error(request, 'Cannot remove the company owner.')
            return redirect('companies:team')

        member_email = member.user.email
        member.delete()

        messages.success(request, f'{member_email} has been removed from the team.')
        return redirect('companies:team')


class CancelInvitationView(TeamRequiredMixin, View):
    """Cancel pending invitation (admin only)."""

    def post(self, request, pk, *args, **kwargs):
        company = request.user.get_company()
        if not company:
            messages.error(request, 'No company found.')
            return redirect('companies:team')

        if not company.is_admin(request.user):
            messages.error(request, 'Only team admins can cancel invitations.')
            return redirect('companies:team')

        invitation = get_object_or_404(TeamInvitation, pk=pk, company=company)
        invitation_email = invitation.email
        invitation.delete()

        messages.success(request, f'Invitation to {invitation_email} has been cancelled.')
        return redirect('companies:team')


class ReminderSettingsView(LoginRequiredMixin, View):
    """Configure payment reminder settings."""
    template_name = 'settings/reminders.html'

    def get_company(self, user):
        """Get or create company for user."""
        company, created = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"}
        )
        return company

    def get_reminder_settings(self, company):
        """Get or create reminder settings for company."""
        settings, created = PaymentReminderSettings.objects.get_or_create(
            company=company
        )
        return settings

    def get(self, request, *args, **kwargs):
        company = self.get_company(request.user)
        reminder_settings = self.get_reminder_settings(company)
        form = PaymentReminderSettingsForm(instance=reminder_settings)

        return render(request, self.template_name, {
            'form': form,
            'reminder_settings': reminder_settings,
        })

    def post(self, request, *args, **kwargs):
        company = self.get_company(request.user)
        reminder_settings = self.get_reminder_settings(company)
        form = PaymentReminderSettingsForm(request.POST, instance=reminder_settings)

        if form.is_valid():
            form.save()
            messages.success(request, 'Payment reminder settings saved successfully!')
            return redirect('companies:reminders')

        return render(request, self.template_name, {
            'form': form,
            'reminder_settings': reminder_settings,
        })
