"""
Site-wide template health checks.

A single unclosed {% block %} in templates/account/signup.html served 500s
on the signup page for five months (Feb-Jul 2026) with nothing catching it.
These tests compile every template and render the critical public pages so
that class of bug fails CI instead of production.
"""
from pathlib import Path

from django.conf import settings
from django.contrib.sites.models import Site
from django.template import engines
from django.test import TestCase

from allauth.socialaccount.models import SocialApp


class TemplateCompileTest(TestCase):
    """Every template in templates/ must compile."""

    def test_all_templates_compile(self):
        engine = engines['django']
        root = Path(settings.BASE_DIR) / 'templates'
        failures = []
        for path in sorted(root.rglob('*.html')):
            name = str(path.relative_to(root))
            try:
                engine.get_template(name)
            except Exception as exc:
                failures.append(f'{name}: {exc}')
        self.assertEqual(failures, [], 'Templates failed to compile:\n' + '\n'.join(failures))


class CriticalPageRenderTest(TestCase):
    """The pages every visitor funnels through must return 200."""

    @classmethod
    def setUpTestData(cls):
        # Signup/login render provider_login_url tags, which need SocialApps
        # (production creates these from env vars in a data migration).
        site = Site.objects.get_current()
        for provider in ('google', 'github'):
            app = SocialApp.objects.create(
                provider=provider, name=provider, client_id='test', secret='test'
            )
            app.sites.add(site)

    def assert_renders(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f'{url} returned {response.status_code}')

    def test_landing(self):
        self.assert_renders('/')

    def test_pricing(self):
        self.assert_renders('/pricing/')

    def test_try(self):
        self.assert_renders('/try/')

    def test_signup(self):
        self.assert_renders('/accounts/signup/')

    def test_login(self):
        self.assert_renders('/accounts/login/')
