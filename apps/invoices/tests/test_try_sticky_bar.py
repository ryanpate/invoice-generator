"""
The /try/ builder on a phone: reach the total and the download without a hunt.

Two problems, one page:

1. The download button sat 2,196px down a 3,843px page at 390x844, with the
   running total only visible in a desktop sidebar that collapses to the
   bottom on mobile. You filled in line items with no feedback and then went
   looking for the payoff. 28% of traffic is mobile.

2. The PDF came back as `inline`, so on mobile Safari it rendered in a tab
   with no obvious way to save it -- a dead end at the moment of success.
   Every other PDF response in the codebase already used `attachment`.

So: a fixed footer on mobile carrying the live total and a submit button,
and the response switched to `attachment`. Switching to attachment also
means the form must stop using target="_blank" -- a download response does
not navigate, so the new tab it opened would just hang around blank.
"""
from django.test import TestCase
from django.urls import reverse


VALID_POST = {
    'company_name': 'Pate Design', 'client_name': 'Northwind Trading',
    'invoice_date': '2026-09-02', 'payment_terms': 'net_30',
    'currency': 'USD', 'template_style': 'clean_slate',
    'item_description_0': 'Brand identity design',
    'item_quantity_0': '12', 'item_rate_0': '150',
}


class PdfDownloadsTest(TestCase):
    """The PDF must download, not render in a tab."""

    def post(self, **overrides):
        data = dict(VALID_POST, **overrides)
        return self.client.post(reverse('try_invoice'), data)

    def test_pdf_is_an_attachment(self):
        response = self.post()
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(
            response['Content-Disposition'].startswith('attachment;'),
            f'PDF still served inline: {response["Content-Disposition"]}',
        )

    def test_filename_names_the_client(self):
        """Every download landing in Downloads as invoice-preview.pdf is useless."""
        disposition = self.post()['Content-Disposition']
        self.assertIn('northwind-trading', disposition.lower())
        self.assertIn('.pdf', disposition)

    def test_blank_client_name_is_still_a_form_error(self):
        """Guard the assumption behind the filename test below."""
        response = self.post(client_name='   ')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Content-Disposition', response.headers)

    def test_filename_survives_an_awkward_client_name(self):
        # All valid form input (non-empty, <=255 chars) but hostile to filenames.
        for name in ('///', 'Ünïcödé Ltd', 'a"b;c', 'A' * 250):
            disposition = self.post(client_name=name)['Content-Disposition']
            self.assertTrue(
                disposition.startswith('attachment; filename="'),
                f'Bad disposition for client {name!r}: {disposition}',
            )
            self.assertTrue(disposition.endswith('.pdf"'))
            # A quote or semicolon would break the header into pieces.
            inner = disposition[len('attachment; filename="'):-1]
            self.assertNotIn('"', inner)
            self.assertNotIn(';', inner)
            self.assertLess(len(inner), 120, f'Filename too long: {len(inner)}')


class StickyBarTest(TestCase):
    """The mobile footer must exist, mirror the total, and submit the form."""

    def setUp(self):
        self.html = self.client.get(reverse('try_invoice')).content.decode()

    def test_bar_is_present(self):
        self.assertIn('id="try-sticky-bar"', self.html)

    def test_bar_carries_a_total_and_a_submit(self):
        bar = self.bar()
        self.assertIn('id="sticky-total"', bar)
        self.assertIn('type="submit"', bar)

    def bar(self):
        start = self.html.index('id="try-sticky-bar"')
        return self.html[start:start + 1600]

    def test_bar_is_mobile_only(self):
        """It duplicates the sidebar, so it must disappear once that is visible."""
        self.assertRegex(self.bar(), r'lg:hidden|md:hidden')

    def test_bar_submits_the_real_form(self):
        """Fixed-position element outside the form still needs to submit it."""
        bar = self.bar()
        self.assertTrue(
            'form="try-invoice-form"' in bar or self.bar_is_inside_form(),
            'Sticky submit button is not wired to the invoice form.',
        )

    def bar_is_inside_form(self):
        form_start = self.html.index('id="try-invoice-form"')
        form_end = self.html.index('</form>', form_start)
        return form_start < self.html.index('id="try-sticky-bar"') < form_end

    def test_page_reserves_room_so_the_bar_covers_nothing(self):
        self.assertRegex(self.html, r'pb-24|pb-28|pb-32|padding-bottom')


class DownloadFlowTest(TestCase):
    """Switching to attachment changes how the form must submit."""

    def setUp(self):
        self.html = self.client.get(reverse('try_invoice')).content.decode()

    def test_form_no_longer_opens_a_blank_tab(self):
        form_tag = self.html[self.html.index('<form method="post" id="try-invoice-form'):][:200]
        self.assertNotIn(
            'target="_blank"', form_tag,
            'A download response does not navigate, so _blank leaves a blank tab.',
        )

    def test_success_copy_matches_a_download(self):
        self.assertNotIn('opened in a new tab', self.html)
        self.assertIn('try-success-banner', self.html)
