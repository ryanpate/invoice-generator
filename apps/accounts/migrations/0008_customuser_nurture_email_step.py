from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_ai_usage_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='nurture_email_step',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
