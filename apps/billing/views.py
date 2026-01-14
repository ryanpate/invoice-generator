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

        # Credit system info
        context['is_subscriber'] = user.is_active_subscriber()
        context['credits'] = {
            'total_available': user.get_available_credits(),
            'free_remaining': user.free_credits_remaining,
            'purchased_balance': user.credits_balance,
            'total_purchased': user.total_credits_purchased,
        }
        context['credit_packs'] = settings.CREDIT_PACKS

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

    # Stripe Connect events
    elif event['type'] == 'account.updated':
        account = event['data']['object']
        handle_connect_account_updated(account)

    return JsonResponse({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout (subscriptions, credit purchases, template purchases, and client payments)."""
    from apps.accounts.models import CustomUser
    from .models import CreditPurchase, TemplatePurchase

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

class CreditsView(LoginRequiredMixin, TemplateView):
    """View and purchase credit packs."""
    template_name = 'billing/credits.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['credit_packs'] = settings.CREDIT_PACKS
        context['credits_balance'] = user.credits_balance
        context['free_credits_remaining'] = user.free_credits_remaining
        context['total_available'] = user.get_available_credits()
        context['total_purchased'] = user.total_credits_purchased
        context['is_subscriber'] = user.is_active_subscriber()
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS

        return context


@login_required
def purchase_credits(request, pack_id):
    """Create Stripe checkout session for credit pack purchase."""
    pack = settings.CREDIT_PACKS.get(pack_id)
    if not pack:
        messages.error(request, 'Invalid credit pack selected.')
        return redirect('billing:credits')

    # Check if Stripe price ID is configured
    if not pack.get('stripe_price_id'):
        messages.error(request, 'Credit packs are not yet available. Please try again later.')
        return redirect('billing:credits')

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY if not settings.STRIPE_LIVE_MODE else settings.STRIPE_LIVE_SECRET_KEY

    try:
        # Create or get Stripe customer
        if not request.user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={'user_id': request.user.id}
            )
            request.user.stripe_customer_id = customer.id
            request.user.save()

        # Create checkout session for one-time payment
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': pack['stripe_price_id'],
                'quantity': 1,
            }],
            mode='payment',  # One-time payment, not subscription
            success_url=request.build_absolute_uri('/billing/credits/success/'),
            cancel_url=request.build_absolute_uri('/billing/credits/'),
            metadata={
                'user_id': str(request.user.id),
                'pack_id': pack_id,
                'credits': str(pack['credits']),
                'type': 'credit_purchase',
            }
        )

        # Create pending purchase record
        from .models import CreditPurchase
        CreditPurchase.objects.create(
            user=request.user,
            stripe_session_id=checkout_session.id,
            pack_id=pack_id,
            credits_amount=pack['credits'],
            price_paid=pack['price'],
            status='pending',
        )

        return redirect(checkout_session.url)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error creating checkout: {str(e)}')
        return redirect('billing:credits')


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

class TemplateStoreView(LoginRequiredMixin, TemplateView):
    """View and purchase premium templates."""
    template_name = 'billing/templates.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['premium_templates'] = settings.PREMIUM_TEMPLATES
        context['bundle'] = settings.PREMIUM_TEMPLATE_BUNDLE
        context['free_templates'] = getattr(settings, 'FREE_TEMPLATES', ['clean_slate'])
        context['invoice_templates'] = settings.INVOICE_TEMPLATES
        context['unlocked_templates'] = user.unlocked_templates or []
        context['available_templates'] = user.get_available_templates()
        context['is_subscriber'] = user.is_active_subscriber()
        context['current_tier'] = user.subscription_tier

        # Check if user has all premium templates (via subscription or purchase)
        all_premium = all(
            t in user.get_available_templates()
            for t in settings.PREMIUM_TEMPLATES.keys()
        )
        context['has_all_premium'] = all_premium

        return context


@login_required
def purchase_template(request, template_id):
    """Create Stripe checkout session for template purchase."""
    # Check if it's a bundle purchase
    is_bundle = template_id == 'bundle'

    if is_bundle:
        item_config = settings.PREMIUM_TEMPLATE_BUNDLE
        price_id = item_config.get('stripe_price_id')
        price = item_config['price']
    else:
        # Individual template purchase
        item_config = settings.PREMIUM_TEMPLATES.get(template_id)
        if not item_config:
            messages.error(request, 'Invalid template selected.')
            return redirect('billing:templates')
        price_id = item_config.get('stripe_price_id')
        price = item_config['price']

    # Check if already owned (individual template)
    if not is_bundle and request.user.has_unlocked_template(template_id):
        messages.info(request, 'You already own this template.')
        return redirect('billing:templates')

    # Check if user already has all premium (via subscription)
    if request.user.is_active_subscriber():
        tier_templates = settings.SUBSCRIPTION_TIERS.get(
            request.user.subscription_tier, {}
        ).get('templates')
        if tier_templates == 'all':
            messages.info(request, 'Your subscription includes all templates.')
            return redirect('billing:templates')

    if not price_id:
        messages.error(request, 'Template purchases are not yet available.')
        return redirect('billing:templates')

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY if not settings.STRIPE_LIVE_MODE else settings.STRIPE_LIVE_SECRET_KEY

    try:
        # Create or get Stripe customer
        if not request.user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={'user_id': request.user.id}
            )
            request.user.stripe_customer_id = customer.id
            request.user.save()

        # Create checkout session for one-time payment
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/billing/templates/success/'),
            cancel_url=request.build_absolute_uri('/billing/templates/'),
            metadata={
                'user_id': str(request.user.id),
                'template_id': template_id,
                'is_bundle': str(is_bundle),
                'type': 'template_purchase',
            }
        )

        # Create pending purchase record
        from .models import TemplatePurchase
        TemplatePurchase.objects.create(
            user=request.user,
            stripe_session_id=checkout_session.id,
            template_id=template_id,
            is_bundle=is_bundle,
            price_paid=price,
            status='pending',
        )

        return redirect(checkout_session.url)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error creating checkout: {str(e)}')
        return redirect('billing:templates')


class TemplatePurchaseSuccessView(LoginRequiredMixin, TemplateView):
    """Template purchase success page."""
    template_name = 'billing/templates_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['unlocked_templates'] = user.unlocked_templates or []
        context['available_templates'] = user.get_available_templates()

        # Get the most recent completed purchase
        from .models import TemplatePurchase
        recent_purchase = TemplatePurchase.objects.filter(
            user=user,
            status='completed'
        ).order_by('-completed_at').first()

        context['recent_purchase'] = recent_purchase
        context['premium_templates'] = settings.PREMIUM_TEMPLATES
        context['invoice_templates'] = settings.INVOICE_TEMPLATES

        return context


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
