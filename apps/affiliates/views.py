from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, CreateView, ListView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from .models import Affiliate, Referral, Commission, AffiliateApplication
from .forms import AffiliateApplicationForm


class AffiliateDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for approved affiliates to view their stats and earnings."""
    template_name = 'affiliates/dashboard.html'

    def get(self, request, *args, **kwargs):
        # Check if user is an approved affiliate
        try:
            affiliate = request.user.affiliate_profile
            if affiliate.status != 'approved':
                messages.warning(request, "Your affiliate account is not yet approved.")
                return redirect('affiliates:apply')
        except Affiliate.DoesNotExist:
            messages.info(request, "You need to apply to become an affiliate first.")
            return redirect('affiliates:apply')

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        affiliate = self.request.user.affiliate_profile

        # Update stats
        affiliate.update_stats()

        # Get recent referrals
        recent_referrals = affiliate.referrals.select_related('referred_user')[:10]

        # Get recent commissions
        recent_commissions = affiliate.commissions.select_related('referral')[:10]

        # Calculate stats for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        monthly_referrals = affiliate.referrals.filter(created_at__gte=thirty_days_ago).count()
        monthly_conversions = affiliate.referrals.filter(
            converted=True,
            converted_at__gte=thirty_days_ago
        ).count()
        monthly_earnings = affiliate.commissions.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        context.update({
            'affiliate': affiliate,
            'recent_referrals': recent_referrals,
            'recent_commissions': recent_commissions,
            'monthly_referrals': monthly_referrals,
            'monthly_conversions': monthly_conversions,
            'monthly_earnings': monthly_earnings,
            'conversion_rate': (affiliate.total_conversions / affiliate.total_referrals * 100) if affiliate.total_referrals > 0 else 0,
        })
        return context


class AffiliateApplyView(LoginRequiredMixin, TemplateView):
    """View for users to apply to become affiliates."""
    template_name = 'affiliates/apply.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if user already has an affiliate profile
        try:
            affiliate = self.request.user.affiliate_profile
            context['affiliate'] = affiliate
            context['already_affiliate'] = True
        except Affiliate.DoesNotExist:
            context['already_affiliate'] = False

        # Check for pending applications
        pending_app = AffiliateApplication.objects.filter(
            user=self.request.user,
            reviewed=False
        ).first()
        context['pending_application'] = pending_app

        # Form for new applications
        context['form'] = AffiliateApplicationForm()

        return context

    def post(self, request, *args, **kwargs):
        # Check if already an affiliate
        if hasattr(request.user, 'affiliate_profile'):
            messages.info(request, "You're already an affiliate!")
            return redirect('affiliates:dashboard')

        # Check for pending application
        if AffiliateApplication.objects.filter(user=request.user, reviewed=False).exists():
            messages.warning(request, "You already have a pending application.")
            return redirect('affiliates:apply')

        form = AffiliateApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            messages.success(request, "Your application has been submitted! We'll review it shortly.")
            return redirect('affiliates:apply')

        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class AffiliateCommissionsView(LoginRequiredMixin, ListView):
    """View all commissions for an affiliate."""
    template_name = 'affiliates/commissions.html'
    context_object_name = 'commissions'
    paginate_by = 20

    def get_queryset(self):
        try:
            affiliate = self.request.user.affiliate_profile
            return affiliate.commissions.select_related('referral').order_by('-created_at')
        except Affiliate.DoesNotExist:
            return Commission.objects.none()


class AffiliateReferralsView(LoginRequiredMixin, ListView):
    """View all referrals for an affiliate."""
    template_name = 'affiliates/referrals.html'
    context_object_name = 'referrals'
    paginate_by = 20

    def get_queryset(self):
        try:
            affiliate = self.request.user.affiliate_profile
            return affiliate.referrals.select_related('referred_user').order_by('-created_at')
        except Affiliate.DoesNotExist:
            return Referral.objects.none()


def referral_redirect(request, code):
    """
    Handle referral link clicks.
    Sets a cookie to track the referral and redirects to the homepage.
    """
    try:
        affiliate = Affiliate.objects.get(referral_code=code.upper(), status='approved')
    except Affiliate.DoesNotExist:
        # Invalid or inactive referral code, just redirect to homepage
        return redirect('landing')

    # Create referral record
    referral = Referral.objects.create(
        affiliate=affiliate,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        landing_page=request.build_absolute_uri()
    )

    # Set cookie and redirect
    response = redirect('landing')
    # Cookie expires in 30 days
    response.set_cookie(
        'ref',
        str(referral.visitor_id),
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        samesite='Lax'
    )
    return response


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Public landing page for affiliate program
class AffiliateProgramView(TemplateView):
    """Public page explaining the affiliate program."""
    template_name = 'affiliates/program.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['commission_rate'] = 20  # 20% commission
        context['cookie_duration'] = 30  # 30 days
        return context
