web: . /opt/venv/bin/activate && python manage.py migrate && python manage.py create_superuser_from_env && gunicorn config.wsgi:application --bind [::]:$PORT --workers 2 --timeout 120
worker: . /opt/venv/bin/activate && celery -A config worker -l info
