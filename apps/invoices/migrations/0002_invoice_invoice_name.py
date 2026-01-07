# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='invoice_name',
            field=models.CharField(blank=True, help_text='Optional name/description for this invoice (e.g., "Website Redesign Project")', max_length=255),
        ),
    ]
