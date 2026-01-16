# Generated migration for payment timestamps

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0005_payment_reminders'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='paid_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp when invoice was marked as paid'
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='sent_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp when invoice was sent to client'
            ),
        ),
    ]
