"""
Four things in the nav, and the surface behind it cut to match.

460 URL routes, 31 models and 9 apps for four PDF downloads a month. Every
feature costs attention as well as maintenance: a new user lands on a
dashboard offering time tracking, recurring invoices, batch CSV, affiliates,
team seats and an AI generator before they have made a single invoice.

So the signed-in nav is Create / Invoices / Time / Settings, and the four
features with no audience yet -- affiliates, client portal, team seats, the
template store -- lose their UI entry points. The code and data stay; this is
reversible in an afternoon if a customer ever asks for one.

The Spanish and French locales go entirely (5 ES and 3 FR users in August,
already noindexed). Their URLs currently return 200, so /es/<path> and
/fr/<path> permanently redirect to the English page rather than 404 -- a
redirect passes on whatever authority they hold; a 404 throws it away.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
STRONG = 'Str0ngPass!2026'


class SignedInNavTest(TestCase):
    """Exactly four destinations, plus logout."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='nav', email='nav@example.test', password=STRONG
        )
        self.client.force_login(self.user)
        self.html = self.client.get(reverse('accounts:dashboard')).content.decode()

    def nav(self):
        start = self.html.index('<nav')
        return self.html[start:self.html.index('</nav>', start)]

    def test_the_four_destinations_are_present(self):
        nav = self.nav()
        for url in (
            reverse('invoices:create'),
            reverse('invoices:list'),
            reverse('invoices:time_list'),
            reverse('accounts:settings'),
        ):
            self.assertIn(url, nav, f'{url} missing from the signed-in nav')

    def test_billing_is_no_longer_a_top_level_nav_item(self):
        """It lives under Settings now; the nav is for doing work."""
        self.assertNotIn(f'"{reverse("billing:overview")}"', self.nav())

    def test_dashboard_still_reachable_from_the_logo(self):
        """Dropping Dashboard from the nav must not orphan it."""
        self.assertIn(reverse('accounts:dashboard'), self.html)

    def test_settings_page_still_links_to_billing(self):
        html = self.client.get(reverse('accounts:settings')).content.decode()
        self.assertIn(reverse('billing:overview'), html)


class HiddenFeaturesTest(TestCase):
    """Hidden from the UI, still working underneath."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='hid', email='hid@example.test', password=STRONG
        )
        self.client.force_login(self.user)

    def test_no_affiliate_link_in_the_footer(self):
        """Checked on /pricing/: the landing page overrides base.html's footer,
        so asserting there would pass whether or not the link was removed."""
        html = self.client.get(reverse('pricing')).content.decode()
        self.assertNotIn(reverse('affiliates:program'), html)

    def test_no_team_tab_in_settings(self):
        """On Business tier, where has_team_seats() is what used to show it."""
        self.user.subscription_tier = 'business'
        self.user.subscription_status = 'active'
        self.user.save()
        self.assertTrue(
            self.user.has_team_seats(),
            'Test precondition broken: this user would never have seen the tab.',
        )
        for page in ('accounts:settings', 'companies:settings',
                     'companies:reminders', 'companies:late_fees'):
            html = self.client.get(reverse(page)).content.decode()
            self.assertNotIn(
                reverse('companies:team'), html,
                f'{page} still shows the Team tab',
            )

    def test_no_template_store_link_anywhere_public(self):
        for page in ('landing', 'pricing'):
            html = self.client.get(reverse(page)).content.decode()
            self.assertNotIn('/billing/templates/', html)

    def test_hidden_routes_still_resolve(self):
        """Hiding is not deleting -- these must not 404 for anyone mid-flow."""
        for name in ('affiliates:program', 'companies:team', 'billing:templates'):
            response = self.client.get(reverse(name))
            self.assertIn(
                response.status_code, (200, 302),
                f'{name} returned {response.status_code}; hiding should not break it',
            )


class LocalesRemovedTest(TestCase):
    """ES and FR are gone, but their URLs still lead somewhere."""

    def test_only_english_is_configured(self):
        from django.conf import settings
        self.assertEqual([code for code, _ in settings.LANGUAGES], ['en'])

    def test_locale_prefixed_urls_redirect_to_english(self):
        for prefix in ('/es', '/fr'):
            for path in ('/pricing/', '/', '/tools/late-fee-calculator/'):
                response = self.client.get(prefix + path)
                self.assertEqual(
                    response.status_code, 301,
                    f'{prefix}{path} returned {response.status_code}, expected a 301',
                )
                self.assertEqual(response['Location'], path)

    def test_english_pages_are_untouched(self):
        for path in ('/', '/pricing/', '/tools/late-fee-calculator/'):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_no_language_switcher(self):
        html = self.client.get(reverse('landing')).content.decode()
        self.assertNotIn('Español', html)
        self.assertNotIn('Français', html)
