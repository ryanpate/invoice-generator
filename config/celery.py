"""
Celery configuration for InvoiceKits.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('invoice_generator')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'process-recurring-invoices-daily': {
        'task': 'apps.invoices.tasks.process_recurring_invoices',
        'schedule': crontab(hour=6, minute=0),  # Run at 6:00 AM UTC daily
        'options': {'queue': 'default'},
    },
    'process-payment-reminders-daily': {
        'task': 'apps.invoices.tasks.process_payment_reminders',
        'schedule': crontab(hour=6, minute=30),  # Run at 6:30 AM UTC daily (after recurring invoices)
        'options': {'queue': 'default'},
    },
}
app.conf.timezone = 'UTC'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
