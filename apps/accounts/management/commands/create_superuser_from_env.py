"""
Management command to create superuser from environment variables.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create superuser from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD env vars'

    def handle(self, *args, **options):
        User = get_user_model()

        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    'DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD must be set'
                )
            )
            return

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # Update password in case it changed
            existing_user.set_password(password)
            existing_user.is_staff = True
            existing_user.is_superuser = True
            existing_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Superuser {email} already exists - password updated')
            )
            return

        User.objects.create_superuser(
            email=email,
            username=email.split('@')[0],
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(f'Superuser {email} created successfully')
        )
