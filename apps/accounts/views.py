"""
Views for accounts app - Dashboard and account management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings

from .models import CustomUser


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view after login."""
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's invoices
        from apps.invoices.models import Invoice
        recent_invoices = Invoice.objects.filter(
            company__user=user
        ).order_by('-created_at')[:5]

        # Calculate stats
        from django.db.models import Sum
        from django.utils import timezone
        current_month = timezone.now().month
        current_year = timezone.now().year

        monthly_invoices = Invoice.objects.filter(
            company__user=user,
            created_at__month=current_month,
            created_at__year=current_year
        )

        context.update({
            'recent_invoices': recent_invoices,
            'invoices_this_month': monthly_invoices.count(),
            'revenue_this_month': monthly_invoices.aggregate(Sum('total'))['total__sum'] or 0,
            'usage_percentage': user.get_usage_percentage(),
            'tier_config': settings.SUBSCRIPTION_TIERS.get(user.subscription_tier, {}),
        })
        return context


class AccountSettingsView(LoginRequiredMixin, TemplateView):
    """Account settings page."""
    template_name = 'settings/account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tier_config'] = settings.SUBSCRIPTION_TIERS.get(
            self.request.user.subscription_tier, {}
        )
        return context


@login_required
def generate_api_key(request):
    """Generate a new API key for the user."""
    if request.method == 'POST':
        if not request.user.has_api_access():
            messages.error(request, 'API access requires a Business or Enterprise plan.')
            return redirect('accounts:settings')

        api_key = request.user.generate_api_key()
        messages.success(
            request,
            f'New API key generated. Make sure to copy it now, you won\'t see it again!'
        )
        # Store temporarily to show once
        request.session['new_api_key'] = api_key

    return redirect('accounts:settings')


@login_required
def delete_account(request):
    """Delete user account."""
    if request.method == 'POST':
        user = request.user
        # Cancel any active subscriptions first
        # TODO: Implement Stripe subscription cancellation

        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('landing')

    return render(request, 'accounts/delete_confirm.html')
