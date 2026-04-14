"""
Run the daily scheduled tasks synchronously.

Invoked by Railway's cron service (replaces Celery worker + beat).
Usage:
    python manage.py run_daily_tasks                 # run all
    python manage.py run_daily_tasks --only recurring
"""
import json
import logging

from django.core.management.base import BaseCommand

from apps.invoices import cron

logger = logging.getLogger(__name__)

TASKS = {
    'recurring': cron.run_recurring_invoices,
    'reminders': cron.run_payment_reminders,
    'late_fees': cron.run_late_fees,
    'nurture': cron.run_nurture_emails,
}


class Command(BaseCommand):
    help = "Run daily scheduled tasks (recurring invoices, reminders, late fees, nurture emails)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            choices=sorted(TASKS.keys()),
            help='Run a single task instead of all of them.',
        )

    def handle(self, *args, **options):
        only = options.get('only')

        if only:
            self.stdout.write(f"Running task: {only}")
            result = TASKS[only]()
            summary = {only: result}
        else:
            self.stdout.write("Running all daily tasks...")
            summary = cron.run_all()

        self.stdout.write(self.style.SUCCESS(json.dumps(summary, indent=2, default=str)))
