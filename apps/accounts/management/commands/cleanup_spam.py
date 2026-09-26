"""
Remove bot accounts and junk /try/ leads left by the September 2026 spam run.

Dry run by default: it prints what it would delete and changes nothing.

    # 1. Look at every eligible account since the spam began
    python manage.py cleanup_spam --since 2026-09-01

    # 2. Narrow to what the spam looks like (regex, case-insensitive, repeatable)
    python manage.py cleanup_spam --since 2026-09-01 --pattern "crypto|bitcoin" --pattern "@spamdomain\\.com$"

    # 3. Same command plus --delete once the list looks right
    python manage.py cleanup_spam --since 2026-09-01 --pattern ... --delete

Deleting a user cascades to their company, invoices and line items.
"""
import re
from datetime import datetime, time

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.invoices.models import Invoice, LineItem, TryLead


class Command(BaseCommand):
    help = 'List (and with --delete, remove) spam accounts and /try/ leads.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since', required=True,
            help='Only consider accounts and leads created on or after this date (YYYY-MM-DD).',
        )
        parser.add_argument(
            '--pattern', action='append', default=[],
            help='Case-insensitive regex. An account matches if its email, company name, '
                 'or any invoice client name/email, notes or line item does. Repeatable.',
        )
        parser.add_argument(
            '--delete', action='store_true',
            help='Actually delete. Requires at least one --pattern.',
        )

    def handle(self, *args, since, pattern, delete, **options):
        try:
            since_dt = timezone.make_aware(
                datetime.combine(datetime.strptime(since, '%Y-%m-%d').date(), time.min)
            )
        except ValueError:
            raise CommandError('--since must be YYYY-MM-DD')
        try:
            patterns = [re.compile(p, re.IGNORECASE) for p in pattern]
        except re.error as e:
            raise CommandError(f'Bad --pattern: {e}')
        if delete and not patterns:
            raise CommandError(
                'Refusing to --delete without a --pattern: every account that signed up '
                'while verification was off is unverified, real users included.'
            )

        users = self.eligible_users(since_dt)
        leads = TryLead.objects.filter(created_at__gte=since_dt)

        matched_users = []
        for user in users:
            texts = self.account_texts(user)
            if not patterns or self.matches(patterns, texts):
                matched_users.append((user, texts))
        matched_leads = [l for l in leads if not patterns or self.matches(patterns, [l.email])]

        self.report(matched_users, matched_leads, bool(patterns))

        if not delete:
            self.stdout.write(self.style.WARNING('\nDry run: nothing deleted. Add --delete to remove the above.'))
            return

        with transaction.atomic():
            for user, _ in matched_users:
                user.delete()
            TryLead.objects.filter(pk__in=[l.pk for l in matched_leads]).delete()
        self.stdout.write(self.style.SUCCESS(
            f'\nDeleted {len(matched_users)} accounts (with their companies and invoices) '
            f'and {len(matched_leads)} /try/ leads.'
        ))

    @staticmethod
    def eligible_users(since_dt):
        """Accounts that could be bots. Anything with a sign of a real person is excluded."""
        verified = EmailAddress.objects.filter(verified=True).values('user_id')
        social = SocialAccount.objects.values('user_id')
        return (
            get_user_model().objects
            .filter(date_joined__gte=since_dt, is_staff=False, is_superuser=False,
                    subscription_tier='free')
            .filter(Q(stripe_customer_id__isnull=True) | Q(stripe_customer_id=''))
            .exclude(pk__in=verified)
            .exclude(pk__in=social)
            .order_by('date_joined')
        )

    @staticmethod
    def account_texts(user):
        invoices = Invoice.objects.filter(company__owner=user) | Invoice.objects.filter(company__user=user)
        texts = [user.email]
        texts += list(invoices.values_list('company__name', flat=True).distinct())
        for name, email, notes in invoices.values_list('client_name', 'client_email', 'notes'):
            texts += [name, email, notes]
        texts += list(
            LineItem.objects.filter(invoice__in=invoices).values_list('description', flat=True)
        )
        return [t for t in texts if t]

    @staticmethod
    def matches(patterns, texts):
        return any(p.search(t) for p in patterns for t in texts)

    def report(self, matched_users, matched_leads, filtered):
        label = 'matching' if filtered else 'eligible (unverified, free, no Stripe, no social login)'
        self.stdout.write(self.style.MIGRATE_HEADING(f'Accounts {label}: {len(matched_users)}'))
        for user, texts in matched_users:
            invoices = Invoice.objects.filter(company__owner=user) | Invoice.objects.filter(company__user=user)
            emailed = invoices.exclude(sent_at__isnull=True).count()
            sample = ' | '.join(t[:40].replace('\n', ' ') for t in texts[1:4])
            self.stdout.write(
                f'  {user.date_joined:%Y-%m-%d}  {user.email}  '
                f'invoices={invoices.distinct().count()} emailed={emailed}  {sample}'
            )
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n/try/ leads {label if filtered else "since date"}: {len(matched_leads)}'))
        for lead in matched_leads:
            self.stdout.write(f'  {lead.created_at:%Y-%m-%d}  {lead.email}  sends={lead.send_count}')
