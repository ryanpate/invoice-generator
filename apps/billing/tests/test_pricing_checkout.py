"""
The pricing page must let a visitor start buying.

Anonymous visitors previously got "Start Free, Upgrade Later" pointing at a
bare signup URL, so the plan they clicked was forgotten the moment they
signed up and they landed on the dashboard instead of Stripe. The pricing
page carried 5 views and 0 signup starts in August 2026.

These tests pin the intent-preserving path: the anonymous CTA must carry
?next= to the checkout URL for the plan, and signing up with that ?next=
must land on checkout rather than the dashboard.
"""
from urllib.parse import quote, unquote

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from allauth.socialaccount.models import SocialApp

User = get_user_model()

PLANS = ('professional', 'business')


class AnonymousPricingCTATest(TestCase):
    """The buy buttons must carry the chosen plan through signup."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)

    def test_cta_links_to_signup_with_checkout_next(self):
        for page in ('/pricing/', '/'):
            html = self.client.get(page).content.decode()
            for plan in PLANS:
                checkout = reverse('billing:checkout', args=[plan])
                expected = (
                    f"{reverse('account_signup')}?plan={plan}&amp;"
                    f"next={quote(checkout, safe='')}"
                )
                self.assertIn(
                    expected, html,
                    f'{page} has no intent-preserving CTA for {plan}. '
                    f'Expected an href containing {expected}',
                )

    def test_cta_does_not_drop_intent(self):
        """A bare signup href on a paid plan is the bug this guards against."""
        html = self.client.get('/pricing/').content.decode()
        self.assertNotIn(
            f'href="{reverse("account_signup")}" class="block w-full text-center btn-primary"',
            html,
            'Paid-plan CTA still points at a bare signup URL, dropping the plan.',
        )


class SignupNextRedirectTest(TestCase):
    """Signing up with ?next=<checkout> must go to checkout, not the dashboard."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)

    def test_signup_honours_next_to_checkout(self):
        checkout = reverse('billing:checkout', args=['professional'])
        response = self.client.post(
            f"{reverse('account_signup')}?next={quote(checkout, safe='')}",
            {
                'first_name': 'Buy', 'last_name': 'Now',
                'email': 'buyer@example.test',
                'password1': 'Str0ngPass!2026', 'password2': 'Str0ngPass!2026',
                'terms': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'], checkout,
            'Signup ignored ?next= and sent the buyer somewhere other than checkout.',
        )
        self.assertTrue(User.objects.filter(email='buyer@example.test').exists())

    def test_form_carries_next_in_the_body(self):
        """The form action has no query string, so `next` must be a form field.

        Posting to the bare action -- what a browser actually does -- is the
        case that drops the plan if the hidden input is missing.
        """
        checkout = reverse('billing:checkout', args=['professional'])
        signup = reverse('account_signup')
        html = self.client.get(
            f"{signup}?plan=professional&next={quote(checkout, safe='')}"
        ).content.decode()
        self.assertIn(
            f'<input type="hidden" name="next" value="{checkout}">', html,
            'Signup form does not carry `next`; the plan is lost on submit.',
        )

        response = self.client.post(signup, {
            'first_name': 'Form', 'last_name': 'Post',
            'email': 'formpost@example.test',
            'password1': 'Str0ngPass!2026', 'password2': 'Str0ngPass!2026',
            'terms': 'on', 'next': checkout, 'plan': 'professional',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], checkout)

    def test_signup_shows_the_chosen_plan(self):
        html = self.client.get(
            f"{reverse('account_signup')}?plan=professional"
        ).content.decode()
        self.assertIn('Pro — $12/month', html)
        self.assertNotIn('3 free invoices every month', html)

    def test_plain_signup_still_shows_the_free_pitch(self):
        html = self.client.get(reverse('account_signup')).content.decode()
        self.assertIn('3 free invoices every month', html)

    def test_next_cannot_redirect_off_site(self):
        """allauth must reject an external `next`; guard against open redirect."""
        response = self.client.post(reverse('account_signup'), {
            'first_name': 'Evil', 'last_name': 'Redirect',
            'email': 'evil@example.test',
            'password1': 'Str0ngPass!2026', 'password2': 'Str0ngPass!2026',
            'terms': 'on', 'next': 'https://evil.example.com/steal',
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.example.com', response['Location'])


class CheckoutRequiresLoginTest(TestCase):
    """Hitting checkout while anonymous must bounce to auth, keeping the plan."""

    def test_anonymous_checkout_redirects_with_next(self):
        for plan in PLANS:
            checkout = reverse('billing:checkout', args=[plan])
            response = self.client.get(checkout)
            self.assertEqual(response.status_code, 302)
            # Django's redirect_to_login leaves slashes unencoded; accept either.
            location = unquote(response['Location'])
            self.assertIn(
                checkout, location,
                f'Anonymous checkout for {plan} lost the plan on redirect.',
            )


class BillingPagesExistTest(TestCase):
    """Every template the billing views name must actually exist.

    /billing/success/ is where Stripe returns a customer after they pay, and
    billing/success.html did not exist -- so the first person to complete a
    checkout would have been charged and then shown a 500. Nothing caught it
    because no checkout has ever completed. billing/cancel.html was missing
    the same way.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='billing', email='billing@example.test',
            password='Str0ngPass!2026',
        )
        self.client.force_login(self.user)

    def test_success_and_cancel_pages_render(self):
        for name in ('billing:success', 'billing:cancel'):
            response = self.client.get(reverse(name))
            self.assertEqual(
                response.status_code, 200,
                f'{name} returned {response.status_code} — a paying customer sees this.',
            )

    def test_every_billing_template_referenced_can_be_loaded(self):
        """Catch the next missing template before a customer does."""
        import re
        from pathlib import Path

        from django.conf import settings as dj_settings
        from django.template.loader import get_template

        source = (Path(dj_settings.BASE_DIR) / 'apps' / 'billing' / 'views.py').read_text()
        referenced = set(re.findall(r"template_name\s*=\s*['\"]([^'\"]+)['\"]", source))
        referenced |= set(re.findall(r"render\(request,\s*['\"]([^'\"]+\.html)['\"]", source))
        self.assertTrue(referenced, 'No templates found in billing/views.py')

        missing = []
        for name in sorted(referenced):
            try:
                get_template(name)
            except Exception:
                missing.append(name)
        self.assertEqual(missing, [], f'billing/views.py names templates that do not exist: {missing}')
