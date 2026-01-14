"""
Stripe Connect Service for handling business payment connections.
"""
import stripe
from decimal import Decimal
from django.conf import settings
from django.utils import timezone


class StripeConnectService:
    """Service for managing Stripe Connect integrations."""

    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )
        self.platform_fee_percent = getattr(
            settings, 'CLIENT_PORTAL_PLATFORM_FEE_PERCENT', 0
        )

    def create_connect_account(self, company):
        """
        Create a Stripe Connect Standard account for a company.

        Args:
            company: Company model instance

        Returns:
            dict with 'success', 'account_id', and 'error' if failed
        """
        try:
            account = self.stripe.Account.create(
                type='standard',
                email=company.email or company.get_effective_owner().email,
                metadata={
                    'company_id': str(company.id),
                    'company_name': company.name,
                }
            )

            # Save account ID to company
            company.stripe_connect_account_id = account.id
            company.save(update_fields=['stripe_connect_account_id'])

            return {
                'success': True,
                'account_id': account.id,
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }

    def create_account_link(self, company, return_url, refresh_url):
        """
        Create an account link for Stripe Connect onboarding.

        Args:
            company: Company model instance
            return_url: URL to redirect after onboarding
            refresh_url: URL if link expires

        Returns:
            dict with 'success', 'url', and 'error' if failed
        """
        if not company.stripe_connect_account_id:
            # Create account first
            result = self.create_connect_account(company)
            if not result['success']:
                return result

        try:
            account_link = self.stripe.AccountLink.create(
                account=company.stripe_connect_account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )

            return {
                'success': True,
                'url': account_link.url,
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }

    def get_account_status(self, company):
        """
        Get the current status of a Stripe Connect account.

        Args:
            company: Company model instance

        Returns:
            dict with account status details
        """
        if not company.stripe_connect_account_id:
            return {
                'connected': False,
                'charges_enabled': False,
                'payouts_enabled': False,
                'onboarding_complete': False,
            }

        try:
            account = self.stripe.Account.retrieve(
                company.stripe_connect_account_id
            )

            # Update company fields
            company.stripe_connect_charges_enabled = account.charges_enabled
            company.stripe_connect_payouts_enabled = account.payouts_enabled
            company.stripe_connect_onboarding_complete = account.details_submitted

            if account.charges_enabled and not company.stripe_connect_connected_at:
                company.stripe_connect_connected_at = timezone.now()

            company.save(update_fields=[
                'stripe_connect_charges_enabled',
                'stripe_connect_payouts_enabled',
                'stripe_connect_onboarding_complete',
                'stripe_connect_connected_at',
            ])

            return {
                'connected': True,
                'account_id': account.id,
                'charges_enabled': account.charges_enabled,
                'payouts_enabled': account.payouts_enabled,
                'onboarding_complete': account.details_submitted,
                'email': account.email,
            }

        except stripe.error.StripeError as e:
            return {
                'connected': False,
                'error': str(e),
            }

    def create_login_link(self, company):
        """
        Create a login link to the Stripe Express Dashboard.

        Args:
            company: Company model instance

        Returns:
            dict with 'success', 'url', and 'error' if failed
        """
        if not company.stripe_connect_account_id:
            return {
                'success': False,
                'error': 'No Stripe Connect account found',
            }

        try:
            login_link = self.stripe.Account.create_login_link(
                company.stripe_connect_account_id
            )

            return {
                'success': True,
                'url': login_link.url,
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }

    def create_checkout_session(self, invoice, client, success_url, cancel_url):
        """
        Create a Stripe Checkout session for invoice payment via Connect.

        Funds go directly to the business's connected account with optional
        platform fee.

        Args:
            invoice: Invoice model instance
            client: Client model instance
            success_url: URL after successful payment
            cancel_url: URL if payment cancelled

        Returns:
            dict with 'success', 'checkout_session', 'checkout_url', and 'error' if failed
        """
        company = invoice.company

        if not company.stripe_connect_account_id:
            return {
                'success': False,
                'error': 'Business has not connected Stripe account',
            }

        if not company.stripe_connect_charges_enabled:
            return {
                'success': False,
                'error': 'Business Stripe account cannot accept charges',
            }

        # Calculate amounts
        amount_cents = int(invoice.total * 100)
        currency = invoice.currency.lower()

        # Calculate platform fee
        platform_fee_cents = 0
        if self.platform_fee_percent > 0:
            platform_fee_cents = int(amount_cents * (self.platform_fee_percent / 100))

        try:
            # Create checkout session with payment going to connected account
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f'Invoice {invoice.invoice_number}',
                            'description': f'Payment to {company.name}',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'client_id': str(client.id),
                    'client_email': client.email,
                    'company_id': str(company.id),
                    'type': 'client_portal_payment',
                },
                'payment_intent_data': {
                    'transfer_data': {
                        'destination': company.stripe_connect_account_id,
                    },
                },
            }

            # Add platform fee if configured
            if platform_fee_cents > 0:
                session_params['payment_intent_data']['application_fee_amount'] = platform_fee_cents

            checkout_session = self.stripe.checkout.Session.create(**session_params)

            return {
                'success': True,
                'checkout_session': checkout_session,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'platform_fee': Decimal(platform_fee_cents) / 100,
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }

    def disconnect_account(self, company):
        """
        Disconnect a Stripe Connect account from the platform.

        Note: This doesn't delete the connected account, just removes
        the connection.

        Args:
            company: Company model instance

        Returns:
            dict with 'success' and 'error' if failed
        """
        if not company.stripe_connect_account_id:
            return {
                'success': False,
                'error': 'No Stripe Connect account to disconnect',
            }

        try:
            # Revoke access via OAuth (if using OAuth flow)
            # For Standard accounts, we just clear our reference
            account_id = company.stripe_connect_account_id

            # Clear company fields
            company.stripe_connect_account_id = None
            company.stripe_connect_onboarding_complete = False
            company.stripe_connect_charges_enabled = False
            company.stripe_connect_payouts_enabled = False
            company.stripe_connect_connected_at = None
            company.save(update_fields=[
                'stripe_connect_account_id',
                'stripe_connect_onboarding_complete',
                'stripe_connect_charges_enabled',
                'stripe_connect_payouts_enabled',
                'stripe_connect_connected_at',
            ])

            return {
                'success': True,
                'disconnected_account': account_id,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def handle_account_updated(self, account_data):
        """
        Handle account.updated webhook event.

        Args:
            account_data: Stripe account data from webhook

        Returns:
            dict with 'success' and 'error' if failed
        """
        from apps.companies.models import Company

        account_id = account_data.get('id')
        if not account_id:
            return {'success': False, 'error': 'No account ID in event'}

        try:
            company = Company.objects.get(stripe_connect_account_id=account_id)

            company.stripe_connect_charges_enabled = account_data.get('charges_enabled', False)
            company.stripe_connect_payouts_enabled = account_data.get('payouts_enabled', False)
            company.stripe_connect_onboarding_complete = account_data.get('details_submitted', False)

            if company.stripe_connect_charges_enabled and not company.stripe_connect_connected_at:
                company.stripe_connect_connected_at = timezone.now()

            company.save(update_fields=[
                'stripe_connect_charges_enabled',
                'stripe_connect_payouts_enabled',
                'stripe_connect_onboarding_complete',
                'stripe_connect_connected_at',
            ])

            return {'success': True, 'company_id': company.id}

        except Company.DoesNotExist:
            return {'success': False, 'error': 'Company not found for account'}

    def handle_checkout_completed(self, session_data):
        """
        Handle checkout.session.completed webhook for client portal payments.

        Args:
            session_data: Stripe checkout session data from webhook

        Returns:
            dict with 'success' and 'error' if failed
        """
        from apps.clients.models import Client, ClientPayment
        from apps.invoices.models import Invoice

        metadata = session_data.get('metadata', {})

        # Only process client portal payments
        if metadata.get('type') != 'client_portal_payment':
            return {'success': True, 'skipped': True}

        invoice_id = metadata.get('invoice_id')
        client_id = metadata.get('client_id')

        if not invoice_id or not client_id:
            return {'success': False, 'error': 'Missing invoice_id or client_id'}

        try:
            invoice = Invoice.objects.get(id=invoice_id)
            client = Client.objects.get(id=client_id)

            # Create or update ClientPayment record
            payment, created = ClientPayment.objects.get_or_create(
                stripe_checkout_session_id=session_data['id'],
                defaults={
                    'client': client,
                    'invoice': invoice,
                    'amount': Decimal(session_data.get('amount_total', 0)) / 100,
                    'currency': session_data.get('currency', 'usd').upper(),
                    'stripe_payment_intent_id': session_data.get('payment_intent', ''),
                    'platform_fee': Decimal(
                        session_data.get('application_fee_amount', 0) or 0
                    ) / 100,
                }
            )

            # Complete the payment (marks invoice as paid)
            payment.complete()

            return {
                'success': True,
                'payment_id': payment.id,
                'invoice_id': invoice.id,
                'created': created,
            }

        except Invoice.DoesNotExist:
            return {'success': False, 'error': f'Invoice {invoice_id} not found'}
        except Client.DoesNotExist:
            return {'success': False, 'error': f'Client {client_id} not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
