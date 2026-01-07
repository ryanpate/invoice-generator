"""
Management command to create superuser from environment variables.
"""
import os
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create superuser from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD env vars'

    def handle(self, *args, **options):
        print("[SUPERUSER] Starting superuser creation command...", flush=True)

        try:
            User = get_user_model()

            email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

            print(f"[SUPERUSER] Email env var set: {bool(email)}", flush=True)
            print(f"[SUPERUSER] Password env var set: {bool(password)}", flush=True)

            if not email or not password:
                print("[SUPERUSER] ERROR: DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD must be set", flush=True)
                return

            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                # Update password in case it changed
                existing_user.set_password(password)
                existing_user.is_staff = True
                existing_user.is_superuser = True
                existing_user.save()
                print(f"[SUPERUSER] User {email} already exists - password updated", flush=True)
                return

            User.objects.create_superuser(
                email=email,
                username=email.split('@')[0],
                password=password
            )
            print(f"[SUPERUSER] Superuser {email} created successfully", flush=True)

        except Exception as e:
            print(f"[SUPERUSER] ERROR: {str(e)}", file=sys.stderr, flush=True)
            raise
