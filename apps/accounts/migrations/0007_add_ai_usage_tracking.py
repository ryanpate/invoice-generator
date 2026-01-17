# Generated migration for AI usage tracking fields
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_customuser_unlocked_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='ai_generations_used',
            field=models.PositiveIntegerField(default=0, help_text='Number of AI invoice generations used this month'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='ai_generations_reset_date',
            field=models.DateField(null=True, blank=True, help_text='Date when AI generation count was last reset'),
        ),
    ]
