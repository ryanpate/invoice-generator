# Generated manually for late fees feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0005_company_stripe_connect_account_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='late_fees_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Enable automatic late fees on overdue invoices'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='late_fee_type',
            field=models.CharField(
                choices=[('flat', 'Flat Fee'), ('percentage', 'Percentage of Invoice')],
                default='flat',
                help_text='Type of late fee to apply',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='late_fee_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Late fee amount (flat fee in currency, or percentage 0-100)',
                max_digits=10
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='late_fee_grace_days',
            field=models.PositiveIntegerField(
                default=3,
                help_text='Days after due date before applying late fee'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='late_fee_max_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Maximum late fee cap (optional)',
                max_digits=10,
                null=True
            ),
        ),
    ]
