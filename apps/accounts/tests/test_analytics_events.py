"""
Conversion events must actually fire, exactly once, on every path.

GA4 reported Key events = 0 on every page for August 2026, and two of the
four events the growth plan called for -- signup_complete and
subscription_started -- did not exist in the codebase at all. Five funnel
changes shipped after that with no way to tell which one moved anything.

The awkward part is that neither event happens on a page the browser is
already sitting on: signup finishes with a redirect, and a subscription
finishes with a redirect back from Stripe. And since /pricing/ now sends a
buyer to signup with ?next=<checkout>, a buyer NEVER sees the dashboard --
so anything dashboard-gated would miss exactly the users who paid.

Hence a one-shot queue: the server drops an event in the session, the next
rendered page emits it and the queue is popped. test_signup_complete_fires_
on_the_buyer_path_too pins the case that motivated it.
"""
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from allauth.socialaccount.models import SocialApp

STRONG = 'Str0ngPass!2026'


class QueueMechanicsTest(TestCase):
    """The queue must fire once and then be empty."""

    def test_queued_event_renders_then_clears(self):
        from apps.accounts.analytics import queue_event

        session = self.client.session
        request = type('R', (), {'session': session})()
        queue_event(request, 'test_event', foo='bar')
        session.save()

        html = self.client.get(reverse('landing')).content.decode()
        self.assertIn('test_event', html)
        # Second render must not repeat it.
        self.assertNotIn('test_event', self.client.get(reverse('landing')).content.decode())

    def test_no_queue_emits_no_script(self):
        html = self.client.get(reverse('landing')).content.decode()
        self.assertNotIn('ga-queued-events', html)

    def test_event_payload_cannot_break_out_of_the_script(self):
        """Params are rendered into a <script>; json_script must neutralise this."""
        from apps.accounts.analytics import queue_event

        session = self.client.session
        request = type('R', (), {'session': session})()
        queue_event(request, 'evil', tier='</script><script>alert(1)</script>')
        session.save()

        html = self.client.get(reverse('landing')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)


class SignupCompleteTest(TestCase):
    """Fires after the account exists, on whichever page comes next."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='t', secret='t'
            )
            app.sites.add(site)

    def test_fires_after_a_plain_signup(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'plain@example.test', 'password1': STRONG,
        }, follow=True)
        self.assertIn('signup_complete', response.content.decode())

    def test_fires_on_the_buyer_path_too(self):
        """A buyer redirects to checkout and never sees the dashboard."""
        checkout = reverse('billing:checkout', args=['professional'])
        response = self.client.post(reverse('account_signup'), {
            'email': 'buyer@example.test', 'password1': STRONG, 'next': checkout,
        })
        self.assertEqual(response['Location'], checkout)
        # The queued event survives the redirect and lands on the next render.
        self.assertIn('signup_complete', self.client.get(reverse('landing')).content.decode())

    def test_fires_only_once(self):
        self.client.post(reverse('account_signup'), {
            'email': 'once@example.test', 'password1': STRONG,
        }, follow=True)
        self.assertNotIn(
            'signup_complete',
            self.client.get(reverse('accounts:dashboard')).content.decode(),
        )


class SubscriptionStartedTest(TestCase):
    """Fires on return from Stripe, once per checkout."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='sub', email='sub@example.test', password=STRONG
        )
        self.client.force_login(self.user)

    def test_does_not_fire_without_a_checkout(self):
        html = self.client.get(reverse('billing:success')).content.decode()
        self.assertNotIn('subscription_started', html)

    def test_fires_once_after_a_checkout_is_initiated(self):
        session = self.client.session
        session['ga_pending_subscription'] = 'professional'
        session.save()

        first = self.client.get(reverse('billing:success')).content.decode()
        self.assertIn('subscription_started', first)
        self.assertIn('professional', first)

        # Refreshing the success page must not double-count revenue.
        second = self.client.get(reverse('billing:success')).content.decode()
        self.assertNotIn('subscription_started', second)


class ExistingEventsStillPresentTest(TestCase):
    """The four events already in the code must not be lost."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='t', secret='t'
            )
            app.sites.add(site)

    def test_events_are_wired(self):
        cases = [
            (reverse('try_invoice'), 'try_pdf_downloaded'),
            (reverse('try_invoice'), 'try_pdf_emailed'),
            (reverse('account_signup'), 'signup_started'),
        ]
        for url, event in cases:
            self.assertIn(
                event, self.client.get(url).content.decode(),
                f'{event} is no longer wired on {url}',
            )
