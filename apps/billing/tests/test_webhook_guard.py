"""
Tests that InvoiceKits ignores checkout events belonging to sibling products.

All of the owner's Stripe products share one account, so every enabled endpoint
receives every other product's events. Without a guard, a sibling app that puts
`user_id` and `plan` in its checkout metadata would upgrade whatever unrelated
InvoiceKits user happens to hold that primary key.
"""
from django.test import TestCase

from apps.accounts.models import CustomUser
from apps.billing.views import handle_checkout_completed


def checkout_session(customer, **metadata):
    return {
        'id': 'cs_test_session',
        'customer': customer,
        'payment_intent': 'pi_test',
        'amount_total': 4900,
        'metadata': metadata,
    }


class ForeignCheckoutEventTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner',
            email='owner@invoicekits.test',
            password='pw',
            stripe_customer_id='cus_invoicekits',
        )

    def test_sibling_product_event_does_not_upgrade_local_user(self):
        """A checkout from another product on the shared account is ignored."""
        session = checkout_session(
            'cus_myrecoverypal',
            user_id=str(self.user.id),
            plan='business',
        )

        handle_checkout_completed(session)

        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, 'free')
        self.assertNotEqual(self.user.subscription_status, 'active')

    def test_session_without_customer_is_ignored(self):
        """No customer on the session means we cannot attribute it — ignore it."""
        session = checkout_session(None, user_id=str(self.user.id), plan='business')

        handle_checkout_completed(session)

        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, 'free')

    def test_own_checkout_still_upgrades_user(self):
        """The real InvoiceKits flow must keep working."""
        session = checkout_session(
            'cus_invoicekits',
            user_id=str(self.user.id),
            plan='business',
        )

        handle_checkout_completed(session)

        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription_tier, 'business')
        self.assertEqual(self.user.subscription_status, 'active')
