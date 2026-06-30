"""
Views for billing and subscription management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
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
        context['is_subscriber'] = user.is_active_subscriber()

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

    # Stripe price IDs (set via env after creating the products in Stripe Dashboard)
    price_ids = {
        'professional': settings.STRIPE_PRO_PRICE_ID,  # $12/month
        'business': settings.STRIPE_BUSINESS_PRICE_ID,  # $49/month
    }

    price_id = price_ids.get(plan)
    if not price_id:
        messages.error(request, 'This plan is not available for purchase yet. Please try again later.')
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

    # Stripe Connect events
    elif event['type'] == 'account.updated':
        account = event['data']['object']
        handle_connect_account_updated(account)

    return JsonResponse({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout (subscriptions, credit purchases, template purchases, and client payments)."""
    from decimal import Decimal
    from apps.accounts.models import CustomUser
    from .models import CreditPurchase, TemplatePurchase
    from apps.affiliates.services.commission_tracker import create_commission_for_purchase

    metadata = session.get('metadata', {})

    # Check if this is a client portal payment
    if metadata.get('type') == 'client_portal_payment':
        from .services.stripe_connect import StripeConnectService
        service = StripeConnectService()
        service.handle_checkout_completed(session)
        return

    user_id = metadata.get('user_id')
    if not user_id:
        return

    # Check if this is a template purchase
    if metadata.get('type') == 'template_purchase':
        try:
            purchase = TemplatePurchase.objects.get(stripe_session_id=session['id'])
            purchase.complete_purchase(
                payment_intent_id=session.get('payment_intent', '')
            )
            # Track affiliate commission
            try:
                user = CustomUser.objects.get(id=user_id)
                amount = Decimal(str(session.get('amount_total', 0))) / 100
                is_bundle = metadata.get('is_bundle') == 'True'
                description = 'Template Bundle' if is_bundle else f"Template: {metadata.get('template_id', 'Unknown')}"
                create_commission_for_purchase(
                    user=user,
                    purchase_type='template',
                    purchase_description=description,
                    purchase_amount=amount,
                    stripe_payment_intent_id=session.get('payment_intent', '')
                )
            except CustomUser.DoesNotExist:
                pass
        except TemplatePurchase.DoesNotExist:
            # Fallback: unlock template directly if purchase record not found
            try:
                user = CustomUser.objects.get(id=user_id)
                template_id = metadata.get('template_id')
                is_bundle = metadata.get('is_bundle') == 'True'
                if is_bundle:
                    user.unlock_all_premium_templates()
                elif template_id:
                    user.unlock_template(template_id)
            except (CustomUser.DoesNotExist, ValueError):
                pass
        return

    # Check if this is a credit purchase
    if 'credits' in metadata:
        try:
            purchase = CreditPurchase.objects.get(stripe_session_id=session['id'])
            purchase.complete_purchase(
                payment_intent_id=session.get('payment_intent', '')
            )
            # Track affiliate commission
            try:
                user = CustomUser.objects.get(id=user_id)
                amount = Decimal(str(session.get('amount_total', 0))) / 100
                credits = metadata.get('credits', '0')
                create_commission_for_purchase(
                    user=user,
                    purchase_type='credit_pack',
                    purchase_description=f'{credits} Credit Pack',
                    purchase_amount=amount,
                    stripe_payment_intent_id=session.get('payment_intent', '')
                )
            except CustomUser.DoesNotExist:
                pass
        except CreditPurchase.DoesNotExist:
            # Fallback: create credits directly if purchase record not found
            try:
                user = CustomUser.objects.get(id=user_id)
                credits = int(metadata.get('credits', 0))
                if credits > 0:
                    user.add_credits(credits)
            except (CustomUser.DoesNotExist, ValueError):
                pass
        return

    # Handle subscription checkout
    plan = metadata.get('plan')
    if user_id and plan:
        try:
            user = CustomUser.objects.get(id=user_id)
            user.subscription_tier = plan
            user.subscription_status = 'active'
            user.save()
            # Track affiliate commission for first subscription payment
            amount = Decimal(str(session.get('amount_total', 0))) / 100
            plan_names = {'starter': 'Starter', 'professional': 'Professional', 'business': 'Business'}
            create_commission_for_purchase(
                user=user,
                purchase_type='subscription',
                purchase_description=f'{plan_names.get(plan, plan.title())} Plan',
                purchase_amount=amount,
                stripe_payment_intent_id=session.get('payment_intent', '')
            )
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


def handle_connect_account_updated(account):
    """Handle Stripe Connect account updates."""
    from .services.stripe_connect import StripeConnectService
    service = StripeConnectService()
    service.handle_account_updated(account)


# Credit Purchase Views

class CreditsView(LoginRequiredMixin, View):
    """Credits/pay-as-you-go was retired — send users to the simplified plans page."""

    def get(self, request, *args, **kwargs):
        return redirect('billing:plans')


@login_required
def purchase_credits(request, pack_id):
    """Credit purchases are retired — redirect to the plans page."""
    return redirect('billing:plans')


class CreditPurchaseSuccessView(LoginRequiredMixin, TemplateView):
    """Credit purchase success page."""
    template_name = 'billing/credits_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['credits_balance'] = user.credits_balance
        context['free_credits_remaining'] = user.free_credits_remaining
        context['total_available'] = user.get_available_credits()

        # Get the most recent completed purchase
        from .models import CreditPurchase
        recent_purchase = CreditPurchase.objects.filter(
            user=user,
            status='completed'
        ).order_by('-completed_at').first()

        context['recent_purchase'] = recent_purchase

        return context


# ============================================================================
# Premium Template Purchase Views
# ============================================================================

# The premium template store was retired — every plan (including Free) now includes
# all templates, so these routes just redirect to the plans page.
class TemplateStoreView(LoginRequiredMixin, View):
    """Template store retired — all templates are included with every plan."""

    def get(self, request, *args, **kwargs):
        return redirect('billing:plans')


@login_required
def purchase_template(request, template_id):
    """Template purchases are retired — all templates are free for every plan."""
    return redirect('billing:plans')


class TemplatePurchaseSuccessView(LoginRequiredMixin, View):
    """Template store retired — redirect to the plans page."""

    def get(self, request, *args, **kwargs):
        return redirect('billing:plans')


# ============================================================================
# Stripe Connect Views (for businesses to receive payments)
# ============================================================================

class StripeConnectStatusView(LoginRequiredMixin, TemplateView):
    """View Stripe Connect status and manage connection."""
    template_name = 'billing/stripe_connect_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get or create company for user
        try:
            company = self.request.user.company
        except:
            company = None

        if company:
            from .services.stripe_connect import StripeConnectService
            service = StripeConnectService()
            status = service.get_account_status(company)
            context['connect_status'] = status
            context['company'] = company
        else:
            context['connect_status'] = {'connected': False}
            context['company'] = None

        return context


@login_required
def stripe_connect_start(request):
    """Start Stripe Connect onboarding."""
    try:
        company = request.user.company
    except:
        messages.error(request, 'Please create a company profile first.')
        return redirect('companies:settings')

    from .services.stripe_connect import StripeConnectService
    service = StripeConnectService()

    return_url = request.build_absolute_uri('/billing/stripe-connect/return/')
    refresh_url = request.build_absolute_uri('/billing/stripe-connect/refresh/')

    result = service.create_account_link(company, return_url, refresh_url)

    if result['success']:
        return redirect(result['url'])
    else:
        messages.error(request, result.get('error', 'Unable to start Stripe Connect.'))
        return redirect('billing:stripe_connect_status')


@login_required
def stripe_connect_return(request):
    """Handle return from Stripe Connect onboarding."""
    try:
        company = request.user.company
    except:
        return redirect('billing:overview')

    from .services.stripe_connect import StripeConnectService
    service = StripeConnectService()

    # Refresh account status
    status = service.get_account_status(company)

    if status.get('charges_enabled'):
        messages.success(
            request,
            'Stripe Connect setup complete! You can now receive payments from clients.'
        )
    elif status.get('onboarding_complete'):
        messages.info(
            request,
            'Your Stripe account is under review. You\'ll be able to accept payments once approved.'
        )
    else:
        messages.warning(
            request,
            'Stripe Connect setup is incomplete. Please complete all required steps.'
        )

    return redirect('billing:stripe_connect_status')


@login_required
def stripe_connect_refresh(request):
    """Handle expired onboarding link - create new one."""
    return redirect('billing:stripe_connect_start')


@login_required
def stripe_connect_dashboard(request):
    """Redirect to Stripe Express Dashboard."""
    try:
        company = request.user.company
    except:
        messages.error(request, 'No company found.')
        return redirect('billing:overview')

    if not company.stripe_connect_account_id:
        messages.error(request, 'Please connect your Stripe account first.')
        return redirect('billing:stripe_connect_status')

    from .services.stripe_connect import StripeConnectService
    service = StripeConnectService()

    result = service.create_login_link(company)

    if result['success']:
        return redirect(result['url'])
    else:
        messages.error(request, result.get('error', 'Unable to access Stripe Dashboard.'))
        return redirect('billing:stripe_connect_status')


@login_required
def stripe_connect_disconnect(request):
    """Disconnect Stripe Connect account."""
    if request.method != 'POST':
        return redirect('billing:stripe_connect_status')

    try:
        company = request.user.company
    except:
        return redirect('billing:overview')

    from .services.stripe_connect import StripeConnectService
    service = StripeConnectService()

    result = service.disconnect_account(company)

    if result['success']:
        messages.success(request, 'Stripe Connect account disconnected.')
    else:
        messages.error(request, result.get('error', 'Unable to disconnect account.'))

    return redirect('billing:stripe_connect_status')
