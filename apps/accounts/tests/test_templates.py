"""
Site-wide template health checks.

A single unclosed {% block %} in templates/account/signup.html served 500s
on the signup page for five months (Feb-Jul 2026) with nothing catching it.
These tests compile every template and render the critical public pages so
that class of bug fails CI instead of production.
"""
import os
import re
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


class CompiledCSSTest(TestCase):
    """Every component class in input.css must survive into the built CSS.

    Tailwind only emits an @layer components rule if it sees the class used
    in a file matched by the `content` globs. form-textarea is applied only
    from Django widget definitions in apps/*/forms.py, which the globs did
    not cover, so the rule was dropped from every production build and all
    textareas rendered unstyled -- and overflowed their container on mobile.
    Nothing caught it because the compiled CSS is gitignored and generated
    at deploy time.
    """

    COMPONENT_RE = re.compile(r'^\s*\.([A-Za-z][\w-]*)\s*\{', re.MULTILINE)

    def test_component_classes_survive_the_build(self):
        source = Path(settings.BASE_DIR) / 'static' / 'src' / 'input.css'
        compiled = Path(settings.BASE_DIR) / 'static' / 'css' / 'tailwind.css'

        layer = source.read_text().split('@layer components', 1)
        self.assertEqual(len(layer), 2, 'No @layer components block in input.css')
        expected = self.COMPONENT_RE.findall(layer[1])
        self.assertTrue(expected, 'No component classes found in input.css')

        if not compiled.exists():
            # CI always builds the CSS before running tests; locally it may
            # not be built yet, and that should not block a developer.
            if os.environ.get('CI'):
                self.fail(f'{compiled} missing -- did the CSS build step run?')
            self.skipTest('static/css/tailwind.css not built; run `npm run build:css`')

        css = compiled.read_text()
        # Tolerate both minified and expanded output (".x{" and ".x {").
        missing = [
            name for name in expected
            if not re.search(rf'\.{re.escape(name)}\s*[{{,:]', css)
        ]
        self.assertEqual(
            missing,
            [],
            'Component classes defined in input.css but absent from the compiled '
            'CSS: ' + ', '.join(missing) + '. Tailwind drops rules it never sees '
            'used -- add the file that applies them to `content` in tailwind.config.js.',
        )
