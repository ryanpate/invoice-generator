# Generated manually for late fees feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0006_add_payment_timestamps'),
    ]

    operations = [
        # Add late fee fields to Invoice
        migrations.AddField(
            model_name='invoice',
            name='late_fees_paused',
            field=models.BooleanField(
                default=False,
                help_text='Pause automatic late fees for this invoice'
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='late_fee_applied',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Amount of late fee applied to this invoice',
                max_digits=12
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='late_fee_applied_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the late fee was applied',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='original_total',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Original total before late fee was applied',
                max_digits=12,
                null=True
            ),
        ),
        # Create LateFeeLog model
        migrations.CreateModel(
            name='LateFeeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fee_type', models.CharField(help_text='Type of fee applied (flat or percentage)', max_length=20)),
                ('fee_amount', models.DecimalField(decimal_places=2, help_text='Amount of late fee applied', max_digits=12)),
                ('days_overdue', models.PositiveIntegerField(help_text='Days past due date when fee was applied')),
                ('invoice_total_before', models.DecimalField(decimal_places=2, help_text='Invoice total before late fee', max_digits=12)),
                ('invoice_total_after', models.DecimalField(decimal_places=2, help_text='Invoice total after late fee', max_digits=12)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('applied_by', models.CharField(default='system', help_text='Who/what applied the fee (system or manual)', max_length=50)),
                ('invoice', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='late_fee_logs', to='invoices.invoice')),
            ],
            options={
                'verbose_name': 'Late Fee Log',
                'verbose_name_plural': 'Late Fee Logs',
                'ordering': ['-applied_at'],
            },
        ),
    ]
