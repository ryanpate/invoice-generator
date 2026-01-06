web: python manage.py migrate && gunicorn config.wsgi:application --bind [::]:$PORT
worker: celery -A config worker -l info
