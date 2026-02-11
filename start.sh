#!/bin/bash
set -e

export LD_LIBRARY_PATH=/nix/var/nix/profiles/default/lib:$LD_LIBRARY_PATH
export GI_TYPELIB_PATH=/nix/var/nix/profiles/default/lib/girepository-1.0

. /opt/venv/bin/activate

case "${SERVICE_TYPE}" in
  "celery-worker")
    echo "[START] Launching celery worker..."
    exec celery -A config worker -l info --concurrency 2
    ;;
  "celery-beat")
    echo "[START] Launching celery beat scheduler..."
    exec celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  *)
    echo "[START] Running migrations..."
    python manage.py migrate
    python manage.py create_superuser_from_env
    python manage.py seed_blog
    echo "[START] Launching gunicorn..."
    exec gunicorn config.wsgi:application --bind [::]:$PORT --workers 1 --timeout 120 --max-requests 500 --max-requests-jitter 50
    ;;
esac
