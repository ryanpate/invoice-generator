"""
The homepage is the product, not a brochure about it.

The old hero was copy plus a static picture of an invoice, with "Start
invoicing free" (a signup wall) as the primary button and "Try it - no
signup" as the polite outline secondary. In August 2026 the homepage drew
36 views at 1.3 seconds of engagement per user -- nobody was reading it.
Meanwhile /try/, the page that actually does something, converted about
half of everyone who reached it (15 views -> 8 PDFs).

So the hero now contains a working invoice builder: your company, your
client, one line item, and a live total. Submitting hands off to /try/ with
every field prefilled, which reuses the tested PDF pipeline rather than
duplicating it and leaves the visitor one click from a finished invoice.

The form is a plain GET so it works with no JavaScript; the live total is
an enhancement on top.
"""
from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse


class HeroBuilderTest(TestCase):
    """The homepage must ship a real form, not a picture of one."""

    def setUp(self):
        self.html = self.client.get(reverse('landing')).content.decode()

    def test_hero_has_a_working_builder_form(self):
        self.assertIn('id="hero-builder"', self.html)
        for field in ('company_name', 'client_name', 'prefill', 'qty', 'rate'):
            self.assertIn(
                f'name="{field}"', self.html,
                f'Hero builder is missing the {field} field.',
            )

    def test_builder_submits_to_the_try_page(self):
        self.assertIn(f'action="{reverse("try_invoice")}"', self.html)
        # GET, so it works without JS and creates no CSRF/state problems.
        self.assertIn('method="get"', self.html.lower())

    def hero_section(self):
        """Just the hero, excluding the nav -- which keeps its own signup link."""
        self.assertIn('class="lp-hero"', self.html)
        start = self.html.index('class="lp-hero"')
        end = self.html.index('</section>', start)
        return self.html[start:end]

    def test_hero_leads_with_the_product_not_the_signup_wall(self):
        """The hero's own call to action must be the builder, not a signup wall."""
        hero = self.hero_section()
        self.assertIn('id="hero-builder"', hero)
        self.assertNotIn(
            reverse('account_signup'), hero,
            'A signup link still competes with the builder inside the hero.',
        )

    def test_builder_is_the_only_submit_in_the_hero(self):
        hero = self.hero_section()
        self.assertEqual(
            hero.count('type="submit"'), 1,
            'The hero should offer one action: create the invoice.',
        )

    def test_live_total_element_present(self):
        self.assertIn('id="hero-total"', self.html)


class TryPrefillTest(TestCase):
    """/try/ must accept everything the hero collects."""

    def get_try(self, **params):
        return self.client.get(f'{reverse("try_invoice")}?{urlencode(params)}')

    def test_prefills_every_hero_field(self):
        response = self.get_try(
            company_name='Pate Design', client_name='Northwind',
            prefill='Brand identity design', qty='12', rate='150',
        )
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="Pate Design"', html)
        self.assertIn('value="Northwind"', html)
        self.assertIn('value="Brand identity design"', html)
        self.assertIn('value="12"', html)
        self.assertIn('value="150"', html)

    def test_bare_prefill_still_works(self):
        """Feature pages and the calculators already link with ?prefill= alone."""
        html = self.get_try(prefill='Late fee').content.decode()
        self.assertIn('value="Late fee"', html)

    def test_no_params_renders_clean_form(self):
        html = self.client.get(reverse('try_invoice')).content.decode()
        self.assertEqual(self.client.get(reverse('try_invoice')).status_code, 200)
        self.assertIn('name="item_description_0"', html)

    def test_junk_numbers_do_not_break_the_page(self):
        response = self.get_try(qty='not-a-number', rate='<script>', prefill='x')
        self.assertEqual(response.status_code, 200, 'Bad qty/rate 500d the builder.')
        self.assertNotIn('<script>alert', response.content.decode())

    def test_prefill_is_escaped(self):
        html = self.get_try(company_name='"><script>alert(1)</script>').content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_overlong_values_are_capped(self):
        html = self.get_try(company_name='A' * 900, prefill='B' * 900).content.decode()
        self.assertNotIn('A' * 600, html)
        self.assertNotIn('B' * 600, html)


class HeroToPdfTest(TestCase):
    """The handoff must actually end in a PDF."""

    def test_prefilled_builder_posts_through_to_a_pdf(self):
        response = self.client.post(reverse('try_invoice'), {
            'company_name': 'Pate Design', 'client_name': 'Northwind',
            'invoice_date': '2026-09-02', 'payment_terms': 'net_30',
            'currency': 'USD', 'template_style': 'clean_slate',
            'item_description_0': 'Brand identity design',
            'item_quantity_0': '12', 'item_rate_0': '150',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
