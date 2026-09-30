from datetime import date

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice


class RequestAccessEnumerationTest(TestCase):
    """The portal must not reveal whether an address belongs to a client."""

    def setUp(self):
        user = CustomUser.objects.create_user(
            username='owner', email='owner@example.test', password='pw-12345678'
        )
        company = Company.objects.create(user=user, owner=user, name='Real Co')
        Invoice.objects.create(
            company=company,
            invoice_number='INV-1',
            client_name='Client',
            client_email='client@example.test',
            invoice_date=date.today(),
            due_date=date.today(),
            status='sent',
        )
        self.url = reverse('clients:request_access')

    def test_known_and_unknown_addresses_get_the_same_response(self):
        known = self.client.post(self.url, {'email': 'client@example.test'})
        unknown = self.client.post(self.url, {'email': 'stranger@example.test'})
        for response in (known, unknown):
            self.assertRedirects(
                response, reverse('clients:check_email'), fetch_redirect_response=False
            )

    def test_only_a_known_address_is_emailed(self):
        self.client.post(self.url, {'email': 'stranger@example.test'})
        self.assertEqual(len(mail.outbox), 0)
        self.client.post(self.url, {'email': 'client@example.test'})
        self.assertEqual([m.to for m in mail.outbox], [['client@example.test']])
