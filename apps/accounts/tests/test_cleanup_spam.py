"""Tests for the cleanup_spam management command."""
from datetime import date
from decimal import Decimal
from io import StringIO

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice, LineItem, TryLead

SINCE = '2000-01-01'


def make_account(email, client_name='Normal Client', **user_fields):
    user = CustomUser.objects.create_user(
        username=email, email=email, password='pw-12345678', **user_fields
    )
    company = Company.objects.create(user=user, owner=user, name=f'{email} co')
    invoice = Invoice.objects.create(
        company=company, invoice_number='INV-1', client_name=client_name,
        invoice_date=date.today(), due_date=date.today(),
    )
    LineItem.objects.create(invoice=invoice, description='Work', quantity=Decimal('1'), rate=Decimal('1'))
    return user


def run(*args):
    out = StringIO()
    call_command('cleanup_spam', '--since', SINCE, *args, stdout=out)
    return out.getvalue()


class CleanupSpamTest(TestCase):
    def setUp(self):
        self.bot = make_account('bot@spam.test', client_name='CLAIM YOUR BITCOIN')
        self.real = make_account('real@person.test')

    def test_dry_run_lists_but_deletes_nothing(self):
        output = run('--pattern', 'bitcoin')
        self.assertIn('bot@spam.test', output)
        self.assertNotIn('real@person.test', output)
        self.assertEqual(CustomUser.objects.count(), 2)

    def test_delete_removes_matching_account_and_its_invoices(self):
        run('--pattern', 'bitcoin', '--delete')
        self.assertFalse(CustomUser.objects.filter(email='bot@spam.test').exists())
        self.assertFalse(Invoice.objects.filter(client_name='CLAIM YOUR BITCOIN').exists())
        self.assertTrue(CustomUser.objects.filter(email='real@person.test').exists())
        self.assertEqual(Invoice.objects.count(), 1)

    def test_delete_without_a_pattern_is_refused(self):
        with self.assertRaises(CommandError):
            run('--delete')
        self.assertEqual(CustomUser.objects.count(), 2)

    def test_protected_accounts_are_never_matched(self):
        verified = make_account('v@spam.test', client_name='bitcoin')
        EmailAddress.objects.create(user=verified, email=verified.email, verified=True, primary=True)
        social = make_account('s@spam.test', client_name='bitcoin')
        SocialAccount.objects.create(user=social, provider='google', uid='1')
        make_account('paid@spam.test', client_name='bitcoin', subscription_tier='professional')
        make_account('cust@spam.test', client_name='bitcoin', stripe_customer_id='cus_1')
        make_account('staff@spam.test', client_name='bitcoin', is_staff=True)

        run('--pattern', 'bitcoin', '--delete')
        remaining = set(CustomUser.objects.values_list('email', flat=True))
        self.assertEqual(remaining, {
            'real@person.test', 'v@spam.test', 's@spam.test',
            'paid@spam.test', 'cust@spam.test', 'staff@spam.test',
        })

    def test_since_excludes_older_accounts(self):
        CustomUser.objects.filter(pk=self.bot.pk).update(date_joined='1999-06-01T00:00:00Z')
        run('--pattern', 'bitcoin', '--delete')
        self.assertTrue(CustomUser.objects.filter(pk=self.bot.pk).exists())

    def test_matching_try_leads_are_deleted(self):
        TryLead.objects.create(email='victim@spam.test')
        TryLead.objects.create(email='lead@person.test')
        run('--pattern', r'@spam\.test$', '--delete')
        self.assertEqual(
            list(TryLead.objects.values_list('email', flat=True)), ['lead@person.test']
        )

    def test_without_pattern_lists_all_eligible_accounts(self):
        output = run()
        self.assertIn('bot@spam.test', output)
        self.assertIn('real@person.test', output)
