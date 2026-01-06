"""
Base Django settings for Invoice Generator Pro.
"""
import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'djstripe',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.companies',
    'apps.invoices',
    'apps.billing',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sites framework
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# django-allauth configuration
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = True
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.api.authentication.APIKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Stripe Configuration
STRIPE_LIVE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY', default='')
STRIPE_TEST_SECRET_KEY = config('STRIPE_TEST_SECRET_KEY', default='')
STRIPE_LIVE_MODE = config('STRIPE_LIVE_MODE', default=False, cast=bool)
DJSTRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# CORS Settings
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv()
)

# Subscription Tiers Configuration
SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'invoices_per_month': 5,
        'templates': ['clean_slate'],
        'batch_upload': False,
        'api_access': False,
        'watermark': True,
        'api_calls_per_month': 0,
    },
    'starter': {
        'name': 'Starter',
        'price': 9,
        'invoices_per_month': 50,
        'templates': ['clean_slate', 'classic_professional'],
        'batch_upload': False,
        'api_access': False,
        'watermark': False,
        'api_calls_per_month': 0,
    },
    'professional': {
        'name': 'Professional',
        'price': 29,
        'invoices_per_month': 200,
        'templates': 'all',
        'batch_upload': True,
        'api_access': False,
        'watermark': False,
        'api_calls_per_month': 0,
    },
    'business': {
        'name': 'Business',
        'price': 79,
        'invoices_per_month': -1,  # Unlimited
        'templates': 'all',
        'batch_upload': True,
        'api_access': True,
        'watermark': False,
        'api_calls_per_month': 1000,
    },
}

# Invoice Templates
INVOICE_TEMPLATES = {
    'clean_slate': {
        'name': 'Clean Slate',
        'description': 'Minimalist white, thin borders, modern sans-serif',
        'best_for': 'Tech companies, startups',
        'premium': False,
    },
    'executive': {
        'name': 'Executive',
        'description': 'Navy & gold accents, serif headings, premium feel',
        'best_for': 'Consulting, legal, finance',
        'premium': False,
    },
    'bold_modern': {
        'name': 'Bold Modern',
        'description': 'Vibrant accent colors, asymmetric layout, large typography',
        'best_for': 'Creative agencies, designers',
        'premium': False,
    },
    'classic_professional': {
        'name': 'Classic Professional',
        'description': 'Traditional layout, subtle grays, highly readable',
        'best_for': 'General business, accounting',
        'premium': False,
    },
    'neon_edge': {
        'name': 'Neon Edge',
        'description': 'Dark mode, neon accents, futuristic',
        'best_for': 'Gaming, tech, entertainment',
        'premium': False,
    },
}

# Currency options
CURRENCIES = [
    ('USD', 'US Dollar ($)'),
    ('EUR', 'Euro (€)'),
    ('GBP', 'British Pound (£)'),
    ('CAD', 'Canadian Dollar (C$)'),
    ('AUD', 'Australian Dollar (A$)'),
    ('JPY', 'Japanese Yen (¥)'),
    ('INR', 'Indian Rupee (₹)'),
]

# Payment terms
PAYMENT_TERMS = [
    ('due_on_receipt', 'Due on Receipt'),
    ('net_15', 'Net 15'),
    ('net_30', 'Net 30'),
    ('net_45', 'Net 45'),
    ('net_60', 'Net 60'),
]
