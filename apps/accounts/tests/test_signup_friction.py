"""
Signup asks for email and password. Nothing else.

The form used to ask for six fields: first name, last name, email, password,
confirm password, and a terms checkbox. Three of them did nothing --
allauth's SignupForm only defines email/password1/password2, so first_name
and last_name were posted and silently discarded (saved as ''), and the
terms checkbox was HTML-`required` only, with no server-side check, so a
POST without it created the account anyway.

In August 2026 the signup page took 8 views and 0 form starts.

These tests pin the reduced form and the fallbacks that let it work: names
are collected later in account settings, and every downstream use of
first_name already degrades to the email address.
"""
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from allauth.socialaccount.models import SocialApp

User = get_user_model()

STRONG = 'Str0ngPass!2026'


def make_user(email):
    """CustomUser keeps AbstractUser's username column, so the manager needs it."""
    return User.objects.create_user(
        username=email.split('@')[0], email=email, password=STRONG
    )


class SignupFormShapeTest(TestCase):
    """Only email and password may be asked for."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)

    def setUp(self):
        self.html = self.client.get(reverse('account_signup')).content.decode()

    def test_asks_for_email_and_password_only(self):
        for name in ('first_name', 'last_name', 'password2'):
            self.assertNotIn(
                f'name="{name}"', self.html,
                f'Signup still asks for {name}; it was never saved or enforced.',
            )

    def test_still_asks_for_email_and_password(self):
        self.assertIn('name="email"', self.html)
        self.assertIn('name="password1"', self.html)

    def test_no_terms_checkbox_but_terms_still_disclosed(self):
        self.assertNotIn('name="terms"', self.html)
        # Consent by submission: the notice must still be visible and linked.
        self.assertIn(reverse('terms'), self.html)
        self.assertIn(reverse('privacy'), self.html)
        self.assertIn('Terms of Service', self.html)
        self.assertIn('Privacy Policy', self.html)

    def test_only_two_visible_inputs(self):
        """A regression here means a field crept back onto the form."""
        import re
        visible = re.findall(r'<input[^>]*name="([^"]+)"', self.html)
        visible = [
            n for n in visible
            if n not in ('csrfmiddlewaretoken', 'next', 'plan')
        ]
        self.assertEqual(
            sorted(visible), ['email', 'password1'],
            f'Signup form fields drifted: {visible}',
        )


class SignupStillWorksTest(TestCase):
    """The reduced form must still create a usable account."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)

    def test_signup_with_two_fields(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'twofields@example.test', 'password1': STRONG,
        })
        self.assertEqual(response.status_code, 302, 'Signup rejected a valid two-field post.')
        user = User.objects.get(email='twofields@example.test')
        self.assertTrue(user.check_password(STRONG))
        self.assertEqual(user.subscription_tier, 'free')
        self.assertTrue(user.can_create_invoice())

    def test_weak_password_still_rejected(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'weak@example.test', 'password1': 'abc',
        })
        self.assertEqual(response.status_code, 200, 'Weak password was accepted.')
        self.assertFalse(User.objects.filter(email='weak@example.test').exists())

    def test_duplicate_email_still_rejected(self):
        make_user('dupe@example.test')
        response = self.client.post(reverse('account_signup'), {
            'email': 'dupe@example.test', 'password1': STRONG,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='dupe@example.test').count(), 1)

    def test_buyer_still_reaches_checkout(self):
        """The two-field form must not break the pricing -> checkout path."""
        checkout = reverse('billing:checkout', args=['professional'])
        response = self.client.post(reverse('account_signup'), {
            'email': 'buyer2@example.test', 'password1': STRONG, 'next': checkout,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], checkout)


class NamelessUserRendersTest(TestCase):
    """Nothing may render a blank greeting now that names start empty."""

    def test_welcome_email_handles_missing_name(self):
        from django.template.loader import render_to_string
        user = make_user('noname@example.test')
        self.assertEqual(user.first_name, '')
        for template in (
            'emails/welcome.html', 'emails/nurture_day2.html', 'emails/nurture_day5.html',
        ):
            html = render_to_string(template, {'user': user, 'site_url': 'https://x.test'})
            self.assertNotIn(
                'Hi ,', html,
                f'{template} renders a dangling greeting for a user with no name.',
            )

    def test_name_can_still_be_added_in_account_settings(self):
        user = make_user('later@example.test')
        self.client.force_login(user)
        html = self.client.get(reverse('accounts:settings')).content.decode()
        self.assertIn('name="first_name"', html, 'No way to add a name after signup.')
