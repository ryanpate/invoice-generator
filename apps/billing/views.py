"""
Views for billing and subscription management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe
import json


class BillingOverviewView(LoginRequiredMixin, TemplateView):
    """Billing overview and subscription management."""
    template_name = 'billing/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['current_tier'] = user.subscription_tier
        context['tier_config'] = settings.SUBSCRIPTION_TIERS.get(user.subscription_tier, {})
        context['all_tiers'] = settings.SUBSCRIPTION_TIERS
        context['usage'] = {
            'invoices_created': user.invoices_created_this_month,
            'api_calls': user.api_calls_this_month,
            'usage_percentage': user.get_usage_percentage(),
        }
        return context


class PlansView(LoginRequiredMixin, TemplateView):
    """View and compare subscription plans."""
    template_name = 'billing/plans.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = settings.SUBSCRIPTION_TIERS
        context['current_tier'] = self.request.user.subscription_tier
        return context


@login_required
def create_checkout_session(request, plan):
    """Create Stripe checkout session for subscription."""
    if plan not in settings.SUBSCRIPTION_TIERS:
        messages.error(request, 'Invalid plan selected.')
        return redirect('billing:plans')

    tier = settings.SUBSCRIPTION_TIERS[plan]
    if tier['price'] == 0:
        # Free plan - just update user
        request.user.subscription_tier = plan
        request.user.subscription_status = 'active'
        request.user.save()
        messages.success(request, f'Switched to {tier["name"]} plan.')
        return redirect('accounts:dashboard')

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY if not settings.STRIPE_LIVE_MODE else settings.STRIPE_LIVE_SECRET_KEY

    # Stripe price IDs (from Stripe Dashboard)
    price_ids = {
        'starter': 'price_1Smy2w6oOlORkbTyjs4TGG8s',       # $9/month
        'professional': 'price_1Smy3O6oOlORkbTySI4fCIod',  # $29/month
        'business': 'price_1Smy4p6oOlORkbTyXe9hIMKE',      # $79/month
    }

    price_id = price_ids.get(plan)
    if not price_id:
        messages.error(request, 'Plan not available for purchase.')
        return redirect('billing:plans')

    try:
        # Create or get Stripe customer
        if not request.user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={'user_id': request.user.id}
            )
            request.user.stripe_customer_id = customer.id
            request.user.save()

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/billing/success/'),
            cancel_url=request.build_absolute_uri('/billing/plans/'),
            metadata={
                'user_id': request.user.id,
                'plan': plan,
            }
        )

        return redirect(checkout_session.url)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error creating checkout: {str(e)}')
        return redirect('billing:plans')


@login_required
def customer_portal(request):
    """Redirect to Stripe Customer Portal for subscription management."""
    if not request.user.stripe_customer_id:
        messages.error(request, 'No billing account found.')
        return redirect('billing:overview')

    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY if not settings.STRIPE_LIVE_MODE else settings.STRIPE_LIVE_SECRET_KEY

    try:
        session = stripe.billing_portal.Session.create(
            customer=request.user.stripe_customer_id,
            return_url=request.build_absolute_uri('/billing/'),
        )
        return redirect(session.url)
    except stripe.error.StripeError as e:
        messages.error(request, f'Error accessing billing portal: {str(e)}')
        return redirect('billing:overview')


class CheckoutSuccessView(LoginRequiredMixin, TemplateView):
    """Checkout success page."""
    template_name = 'billing/success.html'


class CheckoutCancelView(LoginRequiredMixin, TemplateView):
    """Checkout cancelled page."""
    template_name = 'billing/cancel.html'


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY if not settings.STRIPE_LIVE_MODE else settings.STRIPE_LIVE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.DJSTRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Handle specific events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_payment_succeeded(invoice)

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)

    return JsonResponse({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout."""
    from apps.accounts.models import CustomUser

    user_id = session.get('metadata', {}).get('user_id')
    plan = session.get('metadata', {}).get('plan')

    if user_id and plan:
        try:
            user = CustomUser.objects.get(id=user_id)
            user.subscription_tier = plan
            user.subscription_status = 'active'
            user.save()
        except CustomUser.DoesNotExist:
            pass


def handle_subscription_updated(subscription):
    """Handle subscription updates."""
    from apps.accounts.models import CustomUser

    customer_id = subscription.get('customer')
    status = subscription.get('status')

    try:
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
        user.subscription_status = status
        user.save()
    except CustomUser.DoesNotExist:
        pass


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    from apps.accounts.models import CustomUser

    customer_id = subscription.get('customer')

    try:
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
        user.subscription_tier = 'free'
        user.subscription_status = 'canceled'
        user.save()
    except CustomUser.DoesNotExist:
        pass


def handle_payment_succeeded(invoice):
    """Handle successful payment."""
    from apps.accounts.models import CustomUser
    from .models import PaymentHistory

    customer_id = invoice.get('customer')

    try:
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
        PaymentHistory.objects.create(
            user=user,
            stripe_invoice_id=invoice.get('id'),
            amount=invoice.get('amount_paid', 0) / 100,  # Convert from cents
            currency=invoice.get('currency', 'usd').upper(),
            status='succeeded',
            description=f"Subscription payment - {invoice.get('subscription')}"
        )
    except CustomUser.DoesNotExist:
        pass


def handle_payment_failed(invoice):
    """Handle failed payment."""
    from apps.accounts.models import CustomUser

    customer_id = invoice.get('customer')

    try:
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
        user.subscription_status = 'past_due'
        user.save()
    except CustomUser.DoesNotExist:
        pass
