# InvoiceKits iOS App - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a native SwiftUI iOS/iPadOS app backed by a new Django REST API v2 with JWT auth, StoreKit 2 IAP, Face ID, and Live Activities.

**Architecture:** Pure SwiftUI app (iOS 17+, universal) communicating with Django backend via `/api/v2/` endpoints. JWT auth with biometric-protected Keychain storage. StoreKit 2 for subscriptions and credit packs. SwiftData for read-only offline cache.

**Tech Stack:** SwiftUI, SwiftData, StoreKit 2, LocalAuthentication, ActivityKit, AVFoundation, PDFKit, djangorestframework-simplejwt, Apple App Store Server API

---

## Phase 1: Django API v2 — Authentication & Core Infrastructure

### Task 1: Install JWT dependencies and configure DRF

**Files:**
- Modify: `requirements.txt`
- Modify: `config/settings/base.py`

**Step 1: Add djangorestframework-simplejwt to requirements**

Add to `requirements.txt`:
```
djangorestframework-simplejwt==5.3.1
```

**Step 2: Configure JWT in settings**

Add to `config/settings/base.py` after the existing `REST_FRAMEWORK` config:
```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

Add `'rest_framework_simplejwt'` to `THIRD_PARTY_APPS`.

Update `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` to include:
```python
'rest_framework_simplejwt.authentication.JWTAuthentication',
```

**Step 3: Install dependencies locally**

Run: `pip install djangorestframework-simplejwt==5.3.1`

**Step 4: Commit**

```bash
git add requirements.txt config/settings/base.py
git commit -m "feat: add djangorestframework-simplejwt for API v2 auth"
```

---

### Task 2: Create API v2 app structure

**Files:**
- Create: `apps/api_v2/__init__.py`
- Create: `apps/api_v2/apps.py`
- Create: `apps/api_v2/urls.py`
- Create: `apps/api_v2/serializers/__init__.py`
- Create: `apps/api_v2/views/__init__.py`
- Modify: `config/settings/base.py` (add to LOCAL_APPS)
- Modify: `config/urls.py` (add v2 URL include)

**Step 1: Create the app skeleton**

`apps/api_v2/apps.py`:
```python
from django.apps import AppConfig

class ApiV2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api_v2'
    verbose_name = 'API v2'
```

`apps/api_v2/urls.py`:
```python
from django.urls import path, include

app_name = 'api_v2'

urlpatterns = [
    path('auth/', include('apps.api_v2.urls_auth')),
]
```

**Step 2: Register in settings and URLs**

Add `'apps.api_v2'` to `LOCAL_APPS` in `config/settings/base.py`.

Add to `config/urls.py`:
```python
path('api/v2/', include('apps.api_v2.urls')),
```

**Step 3: Commit**

```bash
git add apps/api_v2/ config/settings/base.py config/urls.py
git commit -m "feat: scaffold api_v2 app for iOS backend"
```

---

### Task 3: Implement auth endpoints (register, login, social)

**Files:**
- Create: `apps/api_v2/urls_auth.py`
- Create: `apps/api_v2/views/auth.py`
- Create: `apps/api_v2/serializers/auth.py`
- Create: `apps/api_v2/tests/__init__.py`
- Create: `apps/api_v2/tests/test_auth.py`

**Step 1: Write failing tests**

`apps/api_v2/tests/test_auth.py`:
```python
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import CustomUser


class AuthRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('api_v2:auth-register')

    def test_register_with_valid_data(self):
        data = {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(CustomUser.objects.filter(email='test@example.com').exists())

    def test_register_with_mismatched_passwords(self):
        data = {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'Different123!',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_with_existing_email(self):
        CustomUser.objects.create_user(
            username='existing', email='test@example.com', password='pass123'
        )
        data = {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)


class AuthLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('api_v2:auth-login')
        self.user = CustomUser.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )

    def test_login_with_valid_credentials(self):
        data = {'email': 'test@example.com', 'password': 'StrongPass123!'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_invalid_credentials(self):
        data = {'email': 'test@example.com', 'password': 'WrongPass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, 401)


class AuthRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('api_v2:auth-login')
        self.refresh_url = reverse('api_v2:auth-refresh')
        self.user = CustomUser.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )

    def test_refresh_token(self):
        login_resp = self.client.post(
            self.login_url,
            {'email': 'test@example.com', 'password': 'StrongPass123!'},
            format='json',
        )
        refresh_token = login_resp.data['refresh']
        response = self.client.post(
            self.refresh_url, {'refresh': refresh_token}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)


class AuthSocialAppleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.apple_url = reverse('api_v2:auth-social-apple')

    def test_apple_auth_with_invalid_token(self):
        response = self.client.post(
            self.apple_url, {'id_token': 'invalid'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
```

**Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.api_v2.tests.test_auth -v 2`
Expected: FAIL (URLs don't exist yet)

**Step 3: Implement auth serializers**

`apps/api_v2/serializers/auth.py`:
```python
from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        email = validated_data['email']
        user = CustomUser.objects.create_user(
            username=email.split('@')[0],
            email=email,
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        data['user'] = user
        return data


class AppleSocialAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    first_name = serializers.CharField(required=False, default='')
    last_name = serializers.CharField(required=False, default='')


class GoogleSocialAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
```

**Step 4: Implement auth views**

`apps/api_v2/views/auth.py`:
```python
import jwt
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.api_v2.serializers.auth import (
    RegisterSerializer,
    LoginSerializer,
    AppleSocialAuthSerializer,
    GoogleSocialAuthSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'email': user.email,
            'subscription_tier': user.subscription_tier,
        },
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def apple_social_auth_view(request):
    serializer = AppleSocialAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    id_token = serializer.validated_data['id_token']

    # Fetch Apple's public keys
    try:
        apple_keys_url = 'https://appleid.apple.com/auth/keys'
        apple_keys = requests.get(apple_keys_url, timeout=10).json()
        header = jwt.get_unverified_header(id_token)
        key = None
        for k in apple_keys['keys']:
            if k['kid'] == header['kid']:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break
        if not key:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        payload = jwt.decode(
            id_token,
            key,
            algorithms=['RS256'],
            audience=settings.APPLE_CLIENT_ID,
            issuer='https://appleid.apple.com',
        )
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    email = payload.get('email')
    if not email:
        return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'first_name': serializer.validated_data.get('first_name', ''),
            'last_name': serializer.validated_data.get('last_name', ''),
        },
    )

    return Response(
        get_tokens_for_user(user),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def google_social_auth_view(request):
    serializer = GoogleSocialAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    id_token_str = serializer.validated_data['id_token']

    try:
        google_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}'
        resp = requests.get(google_url, timeout=10)
        if resp.status_code != 200:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        payload = resp.json()
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    email = payload.get('email')
    if not email:
        return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'first_name': payload.get('given_name', ''),
            'last_name': payload.get('family_name', ''),
        },
    )

    return Response(
        get_tokens_for_user(user),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['DELETE'])
def delete_account_view(request):
    user = request.user
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

**Step 5: Wire up auth URLs**

`apps/api_v2/urls_auth.py`:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from apps.api_v2.views.auth import (
    register_view,
    login_view,
    apple_social_auth_view,
    google_social_auth_view,
    delete_account_view,
)

urlpatterns = [
    path('register/', register_view, name='auth-register'),
    path('login/', login_view, name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('social/apple/', apple_social_auth_view, name='auth-social-apple'),
    path('social/google/', google_social_auth_view, name='auth-social-google'),
    path('account/', delete_account_view, name='auth-delete-account'),
]
```

**Step 6: Add APPLE_CLIENT_ID to settings**

Add to `config/settings/base.py`:
```python
APPLE_CLIENT_ID = config('APPLE_CLIENT_ID', default='')
```

**Step 7: Run tests**

Run: `python manage.py test apps.api_v2.tests.test_auth -v 2`
Expected: All register, login, and refresh tests PASS. Apple test passes (invalid token returns 400).

**Step 8: Commit**

```bash
git add apps/api_v2/ config/settings/base.py
git commit -m "feat: implement API v2 auth endpoints (register, login, social, JWT)"
```

---

### Task 4: Add payment_source field to CustomUser

**Files:**
- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/migrations/XXXX_add_payment_source.py` (auto-generated)

**Step 1: Add field to model**

Add to `CustomUser` in `apps/accounts/models.py`:
```python
PAYMENT_SOURCE_CHOICES = [
    ('stripe', 'Stripe'),
    ('apple', 'Apple'),
]

payment_source = models.CharField(
    max_length=10,
    choices=PAYMENT_SOURCE_CHOICES,
    default='stripe',
    help_text='Which payment system manages this user subscription'
)
```

**Step 2: Create and apply migration**

Run: `python manage.py makemigrations accounts -n add_payment_source`
Run: `python manage.py migrate`

**Step 3: Commit**

```bash
git add apps/accounts/
git commit -m "feat: add payment_source field to CustomUser for Apple/Stripe billing sync"
```

---

### Task 5: Add DeviceToken model for push notifications

**Files:**
- Create: `apps/api_v2/models.py`
- Create: `apps/api_v2/admin.py`

**Step 1: Create DeviceToken model**

`apps/api_v2/models.py`:
```python
from django.db import models
from django.conf import settings


class DeviceToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(
        max_length=10,
        choices=[('ios', 'iOS'), ('android', 'Android')],
        default='ios',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"{self.user.email} - {self.platform} ({self.token[:20]}...)"
```

`apps/api_v2/admin.py`:
```python
from django.contrib import admin
from .models import DeviceToken

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'created_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__email', 'token')
```

**Step 2: Create and apply migration**

Run: `python manage.py makemigrations api_v2 -n device_token`
Run: `python manage.py migrate`

**Step 3: Commit**

```bash
git add apps/api_v2/
git commit -m "feat: add DeviceToken model for APNs push notifications"
```

---

## Phase 2: Django API v2 — Invoice Endpoints

### Task 6: Invoice CRUD endpoints

**Files:**
- Create: `apps/api_v2/serializers/invoices.py`
- Create: `apps/api_v2/views/invoices.py`
- Create: `apps/api_v2/urls_invoices.py`
- Modify: `apps/api_v2/urls.py`
- Create: `apps/api_v2/tests/test_invoices.py`

**Step 1: Write failing tests**

`apps/api_v2/tests/test_invoices.py`:
```python
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import Invoice, LineItem


class InvoiceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='testuser', email='test@example.com', password='pass123',
            subscription_tier='professional', subscription_status='active',
        )
        self.company = Company.objects.create(user=self.user, name='Test Co')
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

        self.invoice = Invoice.objects.create(
            company=self.company,
            invoice_number='INV-001',
            client_name='Client A',
            client_email='client@example.com',
            due_date='2026-04-01',
            total=Decimal('100.00'),
        )
        LineItem.objects.create(
            invoice=self.invoice, description='Service', quantity=1, rate=Decimal('100.00'), amount=Decimal('100.00'),
        )

    def test_list_invoices(self):
        url = reverse('api_v2:invoice-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_invoice(self):
        url = reverse('api_v2:invoice-list')
        data = {
            'client_name': 'New Client',
            'client_email': 'new@example.com',
            'payment_terms': 'net_30',
            'currency': 'USD',
            'tax_rate': '10.00',
            'template_style': 'clean_slate',
            'line_items': [
                {'description': 'Web Design', 'quantity': '1', 'rate': '500.00'},
            ],
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Invoice.objects.count(), 2)

    def test_retrieve_invoice(self):
        url = reverse('api_v2:invoice-detail', args=[self.invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['client_name'], 'Client A')

    def test_update_invoice(self):
        url = reverse('api_v2:invoice-detail', args=[self.invoice.id])
        response = self.client.put(url, {
            'client_name': 'Updated Client',
            'client_email': 'client@example.com',
            'payment_terms': 'net_30',
            'currency': 'USD',
            'tax_rate': '0.00',
            'template_style': 'clean_slate',
            'line_items': [
                {'description': 'Updated Service', 'quantity': '2', 'rate': '50.00'},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.client_name, 'Updated Client')

    def test_delete_invoice(self):
        url = reverse('api_v2:invoice-detail', args=[self.invoice.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_download_pdf(self):
        url = reverse('api_v2:invoice-pdf', args=[self.invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_mark_paid(self):
        url = reverse('api_v2:invoice-mark-paid', args=[self.invoice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_mark_sent(self):
        url = reverse('api_v2:invoice-mark-sent', args=[self.invoice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'sent')

    def test_send_email(self):
        url = reverse('api_v2:invoice-send', args=[self.invoice.id])
        response = self.client.post(url, {'message': 'Please pay'}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_toggle_reminders(self):
        url = reverse('api_v2:invoice-toggle-reminders', args=[self.invoice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.reminders_paused)

    def test_toggle_late_fees(self):
        url = reverse('api_v2:invoice-toggle-late-fees', args=[self.invoice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.late_fees_paused)

    def test_unauthenticated_access(self):
        self.client.credentials()  # Remove auth
        url = reverse('api_v2:invoice-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
```

**Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.api_v2.tests.test_invoices -v 2`
Expected: FAIL

**Step 3: Implement serializers**

`apps/api_v2/serializers/invoices.py`:
```python
from rest_framework import serializers
from apps.invoices.models import Invoice, LineItem
from apps.companies.models import Company


class LineItemV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ['id', 'description', 'quantity', 'rate', 'amount', 'order']
        read_only_fields = ['id', 'amount']


class InvoiceListV2Serializer(serializers.ModelSerializer):
    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_name', 'client_name', 'client_email',
            'status', 'total', 'currency', 'currency_symbol',
            'due_date', 'created_at', 'reminders_paused', 'late_fees_paused',
            'late_fee_applied',
        ]


class InvoiceDetailV2Serializer(serializers.ModelSerializer):
    line_items = LineItemV2Serializer(many=True, read_only=True)
    currency_symbol = serializers.CharField(source='get_currency_symbol', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_name', 'status',
            'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_date', 'due_date', 'payment_terms',
            'currency', 'currency_symbol',
            'subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total',
            'notes', 'template_style',
            'line_items',
            'reminders_paused', 'late_fees_paused', 'late_fee_applied',
            'late_fee_applied_at', 'original_total',
            'paid_at', 'sent_at',
            'created_at', 'updated_at',
        ]


class InvoiceCreateV2Serializer(serializers.ModelSerializer):
    line_items = LineItemV2Serializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_name', 'invoice_date', 'payment_terms', 'currency',
            'tax_rate', 'discount_amount', 'notes', 'template_style',
            'line_items',
        ]

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one line item is required.')
        return value

    def validate_template_style(self, value):
        user = self.context['request'].user
        available = user.get_available_templates()
        if value not in available:
            raise serializers.ValidationError(f'Template "{value}" not available on your plan.')
        return value

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')
        user = self.context['request'].user
        company, _ = Company.objects.get_or_create(
            user=user, defaults={'name': f"{user.username}'s Company"}
        )
        invoice = Invoice.objects.create(
            company=company,
            invoice_number=company.get_next_invoice_number(),
            **validated_data,
        )
        for idx, item in enumerate(line_items_data):
            LineItem.objects.create(invoice=invoice, order=idx, **item)
        invoice.due_date = invoice.calculate_due_date()
        invoice.calculate_totals()
        invoice.save()
        user.increment_invoice_count()
        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if line_items_data is not None:
            instance.line_items.all().delete()
            for idx, item in enumerate(line_items_data):
                LineItem.objects.create(invoice=instance, order=idx, **item)
        instance.due_date = instance.calculate_due_date()
        instance.calculate_totals()
        instance.save()
        return instance
```

**Step 4: Implement views**

`apps/api_v2/views/invoices.py`:
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import FileResponse

from apps.invoices.models import Invoice
from apps.invoices.services.pdf_generator import InvoicePDFGenerator
from apps.invoices.services.email_sender import InvoiceEmailService
from apps.api_v2.serializers.invoices import (
    InvoiceListV2Serializer,
    InvoiceDetailV2Serializer,
    InvoiceCreateV2Serializer,
)


class InvoiceV2ViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListV2Serializer
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceCreateV2Serializer
        return InvoiceDetailV2Serializer

    def get_queryset(self):
        qs = Invoice.objects.filter(
            company__user=self.request.user
        ).prefetch_related('line_items').order_by('-created_at')

        # Filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(client_name__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(invoice_name__icontains=search)
            )
        return qs

    def perform_create(self, serializer):
        if not self.request.user.can_create_invoice():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Invoice limit reached for your plan.')
        serializer.save()

    @action(detail=True, methods=['get'], url_path='pdf', url_name='pdf')
    def download_pdf(self, request, pk=None):
        invoice = self.get_object()
        generator = InvoicePDFGenerator(invoice)
        pdf_bytes = generator.generate()
        response = FileResponse(iter([pdf_bytes]), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
        return response

    @action(detail=True, methods=['post'], url_path='send', url_name='send')
    def send_email(self, request, pk=None):
        invoice = self.get_object()
        message = request.data.get('message', '')
        service = InvoiceEmailService(invoice)
        service.send_invoice_email(custom_message=message)
        invoice.mark_as_sent()
        return Response({'status': 'sent'})

    @action(detail=True, methods=['post'], url_path='mark-paid', url_name='mark-paid')
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        invoice.mark_as_paid()
        return Response({'status': 'paid'})

    @action(detail=True, methods=['post'], url_path='mark-sent', url_name='mark-sent')
    def mark_sent(self, request, pk=None):
        invoice = self.get_object()
        invoice.mark_as_sent()
        return Response({'status': 'sent'})

    @action(detail=True, methods=['post'], url_path='toggle-reminders', url_name='toggle-reminders')
    def toggle_reminders(self, request, pk=None):
        invoice = self.get_object()
        invoice.reminders_paused = not invoice.reminders_paused
        invoice.save(update_fields=['reminders_paused'])
        return Response({'reminders_paused': invoice.reminders_paused})

    @action(detail=True, methods=['post'], url_path='toggle-late-fees', url_name='toggle-late-fees')
    def toggle_late_fees(self, request, pk=None):
        invoice = self.get_object()
        invoice.late_fees_paused = not invoice.late_fees_paused
        invoice.save(update_fields=['late_fees_paused'])
        return Response({'late_fees_paused': invoice.late_fees_paused})

    @action(detail=True, methods=['post'], url_path='make-recurring', url_name='make-recurring')
    def make_recurring(self, request, pk=None):
        invoice = self.get_object()
        from apps.invoices.models import RecurringInvoice, RecurringLineItem
        frequency = request.data.get('frequency', 'monthly')
        recurring = RecurringInvoice.objects.create(
            company=invoice.company,
            client_name=invoice.client_name,
            client_email=invoice.client_email,
            client_phone=invoice.client_phone,
            client_address=invoice.client_address,
            currency=invoice.currency,
            payment_terms=invoice.payment_terms,
            tax_rate=invoice.tax_rate,
            discount_amount=invoice.discount_amount,
            notes=invoice.notes,
            template_style=invoice.template_style,
            frequency=frequency,
            status='active',
        )
        for item in invoice.line_items.all():
            RecurringLineItem.objects.create(
                recurring_invoice=recurring,
                description=item.description,
                quantity=item.quantity,
                rate=item.rate,
                order=item.order,
            )
        from apps.api_v2.serializers.invoices import InvoiceDetailV2Serializer
        return Response({'recurring_id': recurring.id}, status=status.HTTP_201_CREATED)
```

**Step 5: Wire up URLs**

`apps/api_v2/urls_invoices.py`:
```python
from rest_framework.routers import DefaultRouter
from apps.api_v2.views.invoices import InvoiceV2ViewSet

router = DefaultRouter()
router.register(r'', InvoiceV2ViewSet, basename='invoice')

urlpatterns = router.urls
```

Update `apps/api_v2/urls.py`:
```python
from django.urls import path, include

app_name = 'api_v2'

urlpatterns = [
    path('auth/', include('apps.api_v2.urls_auth')),
    path('invoices/', include('apps.api_v2.urls_invoices')),
]
```

**Step 6: Run tests**

Run: `python manage.py test apps.api_v2.tests.test_invoices -v 2`
Expected: PASS

**Step 7: Commit**

```bash
git add apps/api_v2/
git commit -m "feat: implement API v2 invoice CRUD with PDF, email, status actions"
```

---

### Task 7: AI generator and voice endpoints

**Files:**
- Create: `apps/api_v2/views/ai.py`
- Create: `apps/api_v2/urls_ai.py`
- Modify: `apps/api_v2/urls.py`

**Step 1: Implement AI views**

`apps/api_v2/views/ai.py`:
```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.invoices.services.ai_generator import AIInvoiceGenerator


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_view(request):
    user = request.user
    if not user.can_use_ai_generator():
        return Response(
            {'error': 'AI generation limit reached for your plan.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    description = request.data.get('description', '').strip()
    if not description:
        return Response(
            {'error': 'Description is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generator = AIInvoiceGenerator()
    result = generator.generate_line_items(description)

    if result.get('error'):
        return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user.increment_ai_generation()
    return Response({
        'line_items': result.get('line_items', []),
        'remaining': user.get_ai_generations_remaining(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def ai_voice_generate_view(request):
    user = request.user
    if not user.can_use_ai_generator():
        return Response(
            {'error': 'AI generation limit reached for your plan.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response(
            {'error': 'Audio file is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generator = AIInvoiceGenerator()
    result = generator.generate_from_audio(audio_file)

    if result.get('error'):
        return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user.increment_ai_generation()
    return Response({
        'line_items': result.get('line_items', []),
        'fields': result.get('fields', {}),
        'transcript': result.get('transcript', ''),
        'remaining': user.get_ai_generations_remaining(),
    })
```

`apps/api_v2/urls_ai.py`:
```python
from django.urls import path
from apps.api_v2.views.ai import ai_generate_view, ai_voice_generate_view

urlpatterns = [
    path('generate/', ai_generate_view, name='ai-generate'),
    path('voice-generate/', ai_voice_generate_view, name='ai-voice-generate'),
]
```

Update `apps/api_v2/urls.py` to add:
```python
path('ai/', include('apps.api_v2.urls_ai')),
```

**Step 2: Commit**

```bash
git add apps/api_v2/
git commit -m "feat: add API v2 AI text and voice generation endpoints"
```

---

### Task 8: Time tracking endpoints

**Files:**
- Create: `apps/api_v2/serializers/time_tracking.py`
- Create: `apps/api_v2/views/time_tracking.py`
- Create: `apps/api_v2/urls_time.py`
- Modify: `apps/api_v2/urls.py`

**Step 1: Implement serializers**

`apps/api_v2/serializers/time_tracking.py`:
```python
from rest_framework import serializers
from apps.invoices.models import TimeEntry, ActiveTimer


class TimeEntryV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = [
            'id', 'description', 'client_name', 'client_email',
            'duration_seconds', 'hourly_rate', 'billable_amount',
            'status', 'date', 'invoice',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'billable_amount', 'invoice', 'created_at', 'updated_at']


class TimeEntryCreateV2Serializer(serializers.ModelSerializer):
    hours = serializers.IntegerField(write_only=True, default=0)
    minutes = serializers.IntegerField(write_only=True, default=0)

    class Meta:
        model = TimeEntry
        fields = [
            'description', 'client_name', 'client_email',
            'hourly_rate', 'date', 'hours', 'minutes',
        ]

    def create(self, validated_data):
        hours = validated_data.pop('hours', 0)
        minutes = validated_data.pop('minutes', 0)
        validated_data['duration_seconds'] = (hours * 3600) + (minutes * 60)
        validated_data['user'] = self.context['request'].user
        entry = TimeEntry.objects.create(**validated_data)
        return entry


class ActiveTimerV2Serializer(serializers.ModelSerializer):
    elapsed_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ActiveTimer
        fields = ['id', 'description', 'client_name', 'started_at', 'elapsed_seconds']

    def get_elapsed_seconds(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.started_at
        return int(delta.total_seconds())
```

**Step 2: Implement views**

`apps/api_v2/views/time_tracking.py`:
```python
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from apps.invoices.models import TimeEntry, ActiveTimer
from apps.invoices.services.time_billing import TimeBillingService
from apps.api_v2.serializers.time_tracking import (
    TimeEntryV2Serializer,
    TimeEntryCreateV2Serializer,
    ActiveTimerV2Serializer,
)


class TimeEntryV2ViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TimeEntryCreateV2Serializer
        return TimeEntryV2Serializer

    def get_queryset(self):
        qs = TimeEntry.objects.filter(user=self.request.user).order_by('-date', '-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(description__icontains=search) | Q(client_name__icontains=search)
            )
        return qs


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_start(request):
    user = request.user
    if not user.can_start_timer():
        return Response(
            {'error': 'Timer limit reached for your plan.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    timer = ActiveTimer.objects.create(
        user=user,
        description=request.data.get('description', ''),
        client_name=request.data.get('client_name', ''),
    )
    return Response(ActiveTimerV2Serializer(timer).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_stop(request, timer_id):
    try:
        timer = ActiveTimer.objects.get(id=timer_id, user=request.user)
    except ActiveTimer.DoesNotExist:
        return Response({'error': 'Timer not found'}, status=status.HTTP_404_NOT_FOUND)

    duration = timezone.now() - timer.started_at
    entry = TimeEntry.objects.create(
        user=request.user,
        description=timer.description,
        client_name=timer.client_name,
        duration_seconds=int(duration.total_seconds()),
        hourly_rate=request.data.get('hourly_rate', 0),
        date=timezone.now().date(),
    )
    timer.delete()
    return Response(TimeEntryV2Serializer(entry).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def timer_discard(request, timer_id):
    try:
        timer = ActiveTimer.objects.get(id=timer_id, user=request.user)
    except ActiveTimer.DoesNotExist:
        return Response({'error': 'Timer not found'}, status=status.HTTP_404_NOT_FOUND)
    timer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def timer_status(request):
    timers = ActiveTimer.objects.filter(user=request.user)
    return Response(ActiveTimerV2Serializer(timers, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bill_time(request):
    entry_ids = request.data.get('entry_ids', [])
    grouping = request.data.get('grouping', 'detailed')

    entries = TimeEntry.objects.filter(
        id__in=entry_ids, user=request.user, status='unbilled'
    )
    if not entries.exists():
        return Response({'error': 'No unbilled entries found'}, status=status.HTTP_400_BAD_REQUEST)

    service = TimeBillingService(request.user)
    invoice = service.create_invoice_from_entries(entries, grouping_mode=grouping)
    return Response({'invoice_id': invoice.id}, status=status.HTTP_201_CREATED)
```

`apps/api_v2/urls_time.py`:
```python
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.api_v2.views.time_tracking import (
    TimeEntryV2ViewSet, timer_start, timer_stop, timer_discard, timer_status, bill_time,
)

router = DefaultRouter()
router.register(r'entries', TimeEntryV2ViewSet, basename='time-entry')

urlpatterns = router.urls + [
    path('timer/start/', timer_start, name='timer-start'),
    path('timer/<int:timer_id>/stop/', timer_stop, name='timer-stop'),
    path('timer/<int:timer_id>/discard/', timer_discard, name='timer-discard'),
    path('timer/status/', timer_status, name='timer-status'),
    path('entries/bill/', bill_time, name='time-bill'),
]
```

Update `apps/api_v2/urls.py` to add:
```python
path('time/', include('apps.api_v2.urls_time')),
```

**Step 3: Commit**

```bash
git add apps/api_v2/
git commit -m "feat: add API v2 time tracking endpoints with timer and billing"
```

---

### Task 9: Recurring invoices, company, settings, billing, and client analytics endpoints

**Files:**
- Create: `apps/api_v2/serializers/recurring.py`
- Create: `apps/api_v2/serializers/company.py`
- Create: `apps/api_v2/serializers/billing.py`
- Create: `apps/api_v2/views/recurring.py`
- Create: `apps/api_v2/views/company.py`
- Create: `apps/api_v2/views/billing.py`
- Create: `apps/api_v2/views/clients.py`
- Create: `apps/api_v2/urls_recurring.py`
- Create: `apps/api_v2/urls_company.py`
- Create: `apps/api_v2/urls_billing.py`
- Create: `apps/api_v2/urls_clients.py`
- Modify: `apps/api_v2/urls.py`

This is a large task. Implement each sub-module following the same pattern as Tasks 6-8:
- Serializers that mirror the Django models
- ViewSets or function-based views
- URL routing
- Wire into main `apps/api_v2/urls.py`

**Recurring invoices** — CRUD ViewSet + toggle status + generate now actions.

**Company** — Single-object GET/PUT for company profile. Separate POST/DELETE endpoints for logo and signature uploads (multipart).

**Settings** — GET/PUT for `PaymentReminderSettings` and late fee settings on Company model.

**Billing** — GET usage stats, GET entitlements (what features the user has access to), POST verify Apple receipt, POST register device token, POST Apple server notifications webhook.

**Client analytics** — GET endpoint that accepts `?email=` param and returns payment rating + average days from `ClientPaymentAnalytics` service.

**Final `apps/api_v2/urls.py`:**
```python
from django.urls import path, include

app_name = 'api_v2'

urlpatterns = [
    path('auth/', include('apps.api_v2.urls_auth')),
    path('invoices/', include('apps.api_v2.urls_invoices')),
    path('ai/', include('apps.api_v2.urls_ai')),
    path('time/', include('apps.api_v2.urls_time')),
    path('recurring/', include('apps.api_v2.urls_recurring')),
    path('company/', include('apps.api_v2.urls_company')),
    path('billing/', include('apps.api_v2.urls_billing')),
    path('clients/', include('apps.api_v2.urls_clients')),
]
```

**Key billing endpoint — Apple receipt verification:**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_apple_receipt(request):
    """Verify Apple IAP receipt and update user subscription."""
    jws_transaction = request.data.get('transaction_jws')
    if not jws_transaction:
        return Response({'error': 'transaction_jws required'}, status=400)

    # Decode and verify the JWS with Apple's public key
    # Map product ID to subscription tier
    # Update user.subscription_tier, user.subscription_status, user.payment_source='apple'
    # Return updated entitlements
    ...
```

**Apple Server Notifications v2 webhook:**
```python
@api_view(['POST'])
@permission_classes([AllowAny])
def apple_server_notification(request):
    """Handle Apple App Store Server Notifications V2."""
    # Verify signed payload from Apple
    # Handle: DID_RENEW, DID_CHANGE_RENEWAL_STATUS, EXPIRED, REFUND, GRACE_PERIOD_EXPIRED
    # Update user subscription_tier and subscription_status accordingly
    ...
```

**Step: Commit**

```bash
git add apps/api_v2/
git commit -m "feat: add API v2 recurring, company, settings, billing, and client endpoints"
```

---

## Phase 3: Xcode Project & iOS App Foundation

### Task 10: Create Xcode project

**Step 1: Create project directory**

```bash
mkdir -p ios/InvoiceKits
```

**Step 2: Create Xcode project**

Open Xcode and create a new project:
- Template: App
- Product Name: InvoiceKits
- Team: (your team)
- Organization Identifier: com.invoicekits
- Interface: SwiftUI
- Language: Swift
- Storage: SwiftData
- Target: iOS 17.0
- Save into: `ios/InvoiceKits/`

Check "Include Tests".

**Step 3: Add Widget Extension target**

In Xcode: File > New > Target > Widget Extension
- Name: InvoiceKitsWidget
- Check "Include Live Activity"

**Step 4: Configure capabilities**

In Signing & Capabilities for main target, add:
- Push Notifications
- Sign in with Apple
- In-App Purchase
- Associated Domains (for universal links if needed later)

**Step 5: Configure entitlements**

Verify `InvoiceKits.entitlements` contains:
```xml
<key>aps-environment</key>
<string>development</string>
<key>com.apple.developer.applesignin</key>
<array><string>Default</string></array>
<key>com.apple.developer.in-app-payments</key>
<array/>
```

**Step 6: Commit**

```bash
git add ios/
git commit -m "feat: create Xcode project with SwiftUI, SwiftData, Widget Extension"
```

---

### Task 11: Implement Keychain and Biometric managers

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Services/KeychainManager.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Services/BiometricManager.swift`

**Step 1: KeychainManager**

```swift
import Foundation
import Security

final class KeychainManager {
    static let shared = KeychainManager()
    private init() {}

    private let service = "com.invoicekits.app"

    func save(_ data: Data, for key: String, biometricProtected: Bool = false) throws {
        try? delete(for: key)

        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
        ]

        if biometricProtected {
            let access = SecAccessControlCreateWithFlags(
                nil,
                kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
                .biometryCurrentSet,
                nil
            )
            query[kSecAttrAccessControl as String] = access as Any
        }

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status)
        }
    }

    func load(for key: String) throws -> Data {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else {
            throw KeychainError.loadFailed(status)
        }
        return data
    }

    func delete(for key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(query as CFDictionary)
    }

    enum KeychainError: Error {
        case saveFailed(OSStatus)
        case loadFailed(OSStatus)
    }
}
```

**Step 2: BiometricManager**

```swift
import LocalAuthentication

@Observable
final class BiometricManager {
    var isAuthenticated = false
    var biometricType: LABiometryType = .none

    private let context = LAContext()

    var isBiometricAvailable: Bool {
        context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil)
    }

    var biometricName: String {
        switch context.biometryType {
        case .faceID: return "Face ID"
        case .touchID: return "Touch ID"
        case .opticID: return "Optic ID"
        default: return "Biometrics"
        }
    }

    func authenticate() async -> Bool {
        let context = LAContext()
        context.localizedCancelTitle = "Use Passcode"

        do {
            let success = try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: "Unlock InvoiceKits"
            )
            await MainActor.run { isAuthenticated = success }
            return success
        } catch {
            return false
        }
    }

    func checkBiometricType() {
        let context = LAContext()
        context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil)
        biometricType = context.biometryType
    }
}
```

**Step 3: Commit**

```bash
git add ios/
git commit -m "feat: implement KeychainManager and BiometricManager for Face ID auth"
```

---

### Task 12: Implement APIClient with JWT auth

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/App/Constants.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Services/APIClient.swift`

**Step 1: Constants**

```swift
import Foundation

enum Constants {
    #if DEBUG
    static let apiBaseURL = URL(string: "http://localhost:8000/api/v2")!
    #else
    static let apiBaseURL = URL(string: "https://www.invoicekits.com/api/v2")!
    #endif

    enum StoreKit {
        static let proMonthly = "com.invoicekits.pro.monthly"
        static let proAnnual = "com.invoicekits.pro.annual"
        static let businessMonthly = "com.invoicekits.business.monthly"
        static let businessAnnual = "com.invoicekits.business.annual"
        static let credits10 = "com.invoicekits.credits.10"
        static let credits25 = "com.invoicekits.credits.25"
        static let credits50 = "com.invoicekits.credits.50"

        static let subscriptionIDs = [proMonthly, proAnnual, businessMonthly, businessAnnual]
        static let creditIDs = [credits10, credits25, credits50]
    }
}
```

**Step 2: APIClient**

```swift
import Foundation

@Observable
final class APIClient {
    private(set) var accessToken: String?
    private(set) var refreshToken: String?

    private let keychain = KeychainManager.shared
    private let session = URLSession.shared
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        d.dateDecodingStrategy = .iso8601
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    init() {
        loadTokens()
    }

    var isAuthenticated: Bool { accessToken != nil }

    // MARK: - Token Management

    func saveTokens(access: String, refresh: String) {
        accessToken = access
        refreshToken = refresh
        try? keychain.save(Data(access.utf8), for: "access_token")
        try? keychain.save(Data(refresh.utf8), for: "refresh_token")
    }

    func clearTokens() {
        accessToken = nil
        refreshToken = nil
        try? keychain.delete(for: "access_token")
        try? keychain.delete(for: "refresh_token")
    }

    private func loadTokens() {
        if let data = try? keychain.load(for: "access_token") {
            accessToken = String(data: data, encoding: .utf8)
        }
        if let data = try? keychain.load(for: "refresh_token") {
            refreshToken = String(data: data, encoding: .utf8)
        }
    }

    // MARK: - Requests

    func request<T: Decodable>(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        var url = Constants.apiBaseURL.appendingPathComponent(path)
        if let queryItems {
            var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
            components.queryItems = queryItems
            url = components.url!
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body {
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        let httpResponse = response as! HTTPURLResponse

        if httpResponse.statusCode == 401 {
            // Try token refresh
            if try await refreshAccessToken() {
                return try await self.request(method, path: path, body: body, queryItems: queryItems)
            }
            throw APIError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode, data)
        }

        return try decoder.decode(T.self, from: data)
    }

    func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem]? = nil) async throws -> T {
        try await request("GET", path: path, queryItems: queryItems)
    }

    func post<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("POST", path: path, body: body)
    }

    func put<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("PUT", path: path, body: body)
    }

    func delete(_ path: String) async throws {
        let _: EmptyResponse = try await request("DELETE", path: path)
    }

    // MARK: - Token Refresh

    private func refreshAccessToken() async throws -> Bool {
        guard let refresh = refreshToken else { return false }

        struct RefreshBody: Encodable { let refresh: String }
        struct RefreshResponse: Decodable { let access: String }

        var request = URLRequest(url: Constants.apiBaseURL.appendingPathComponent("auth/token/refresh/"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(RefreshBody(refresh: refresh))

        let (data, response) = try await session.data(for: request)
        guard (response as! HTTPURLResponse).statusCode == 200 else {
            clearTokens()
            return false
        }

        let result = try decoder.decode(RefreshResponse.self, from: data)
        accessToken = result.access
        try? keychain.save(Data(result.access.utf8), for: "access_token")
        return true
    }

    // MARK: - Multipart Upload

    func upload<T: Decodable>(_ path: String, fileData: Data, filename: String, mimeType: String) async throws -> T {
        let url = Constants.apiBaseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
            throw APIError.httpError((response as! HTTPURLResponse).statusCode, data)
        }
        return try decoder.decode(T.self, from: data)
    }
}

enum APIError: Error {
    case unauthorized
    case httpError(Int, Data)
}

struct EmptyResponse: Decodable {}
```

**Step 3: Commit**

```bash
git add ios/
git commit -m "feat: implement APIClient with JWT auth, token refresh, and multipart upload"
```

---

### Task 13: Implement AuthManager (login, register, social)

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Services/AuthManager.swift`

Handles sign in with Apple (AuthenticationServices), Google Sign-In (GoogleSignIn SDK via SPM), and email/password auth. Calls `APIClient` to exchange tokens with the backend.

```swift
import AuthenticationServices
import SwiftUI

@Observable
final class AuthManager {
    var isLoggedIn = false
    var currentUser: UserInfo?

    private let api: APIClient

    init(api: APIClient) {
        self.api = api
        self.isLoggedIn = api.isAuthenticated
    }

    struct AuthResponse: Decodable {
        let access: String
        let refresh: String
        let user: UserInfo
    }

    struct UserInfo: Decodable, Sendable {
        let id: Int
        let email: String
        let subscriptionTier: String
    }

    func login(email: String, password: String) async throws {
        struct Body: Encodable { let email: String; let password: String }
        let response: AuthResponse = try await api.post("auth/login/", body: Body(email: email, password: password))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func register(email: String, password: String, passwordConfirm: String) async throws {
        struct Body: Encodable { let email: String; let password: String; let passwordConfirm: String }
        let response: AuthResponse = try await api.post("auth/register/", body: Body(email: email, password: password, passwordConfirm: passwordConfirm))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func signInWithApple(authorization: ASAuthorization) async throws {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let tokenData = credential.identityToken,
              let idToken = String(data: tokenData, encoding: .utf8) else {
            throw AuthError.invalidCredential
        }

        struct Body: Encodable {
            let idToken: String
            let firstName: String
            let lastName: String
        }

        let body = Body(
            idToken: idToken,
            firstName: credential.fullName?.givenName ?? "",
            lastName: credential.fullName?.familyName ?? ""
        )

        let response: AuthResponse = try await api.post("auth/social/apple/", body: body)
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func signInWithGoogle(idToken: String) async throws {
        struct Body: Encodable { let idToken: String }
        let response: AuthResponse = try await api.post("auth/social/google/", body: Body(idToken: idToken))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func logout() {
        api.clearTokens()
        currentUser = nil
        isLoggedIn = false
    }

    func deleteAccount() async throws {
        try await api.delete("auth/account/")
        logout()
    }

    enum AuthError: Error {
        case invalidCredential
    }
}
```

**Commit:**

```bash
git add ios/
git commit -m "feat: implement AuthManager with Apple, Google, and email auth"
```

---

### Task 14: Implement StoreManager (StoreKit 2)

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Services/StoreManager.swift`

```swift
import StoreKit

@Observable
final class StoreManager {
    private(set) var subscriptions: [Product] = []
    private(set) var creditPacks: [Product] = []
    private(set) var currentSubscription: Product.SubscriptionInfo.Status?
    private(set) var purchasedProductIDs: Set<String> = []

    private let api: APIClient
    private var updateListenerTask: Task<Void, Never>?

    init(api: APIClient) {
        self.api = api
        updateListenerTask = listenForTransactions()
    }

    func loadProducts() async {
        do {
            let products = try await Product.products(for:
                Constants.StoreKit.subscriptionIDs + Constants.StoreKit.creditIDs
            )
            subscriptions = products.filter { Constants.StoreKit.subscriptionIDs.contains($0.id) }
                .sorted { $0.price < $1.price }
            creditPacks = products.filter { Constants.StoreKit.creditIDs.contains($0.id) }
                .sorted { $0.price < $1.price }
        } catch {
            print("Failed to load products: \(error)")
        }
    }

    func purchase(_ product: Product) async throws -> Bool {
        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            await verifyWithBackend(transaction)
            await transaction.finish()
            return true
        case .userCancelled:
            return false
        case .pending:
            return false
        @unknown default:
            return false
        }
    }

    func restorePurchases() async {
        try? await AppStore.sync()
        await refreshEntitlements()
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw StoreError.verificationFailed
        case .verified(let safe):
            return safe
        }
    }

    private func verifyWithBackend(_ transaction: Transaction) async {
        guard let jwsRepresentation = transaction.jwsRepresentation else { return }
        struct Body: Encodable { let transactionJws: String }
        let _: EmptyResponse? = try? await api.post("billing/verify-receipt/", body: Body(transactionJws: jwsRepresentation))
    }

    private func refreshEntitlements() async {
        for await result in Transaction.currentEntitlements {
            if let transaction = try? checkVerified(result) {
                purchasedProductIDs.insert(transaction.productID)
            }
        }
    }

    private func listenForTransactions() -> Task<Void, Never> {
        Task.detached {
            for await result in Transaction.updates {
                if let transaction = try? self.checkVerified(result) {
                    await self.verifyWithBackend(transaction)
                    await transaction.finish()
                }
            }
        }
    }

    enum StoreError: Error {
        case verificationFailed
    }
}
```

**Commit:**

```bash
git add ios/
git commit -m "feat: implement StoreManager with StoreKit 2 subscriptions and consumables"
```

---

### Task 15: SwiftData models

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Models/Invoice.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Models/LineItem.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Models/TimeEntry.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Models/Company.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Models/User.swift`

These are SwiftData `@Model` classes for local caching, plus `Codable` structs for API responses. Example for Invoice:

```swift
import SwiftData
import Foundation

// API response struct
struct InvoiceResponse: Codable, Identifiable {
    let id: Int
    let invoiceNumber: String
    let invoiceName: String?
    let status: String
    let clientName: String
    let clientEmail: String
    let clientPhone: String?
    let clientAddress: String?
    let invoiceDate: String
    let dueDate: String
    let paymentTerms: String
    let currency: String
    let currencySymbol: String
    let subtotal: String
    let taxRate: String
    let taxAmount: String
    let discountAmount: String
    let total: String
    let notes: String?
    let templateStyle: String
    let lineItems: [LineItemResponse]?
    let remindersPaused: Bool
    let lateFeesPaused: Bool
    let lateFeeApplied: String?
    let paidAt: String?
    let sentAt: String?
    let createdAt: String
    let updatedAt: String
}

// SwiftData cache model
@Model
final class CachedInvoice {
    @Attribute(.unique) var serverId: Int
    var invoiceNumber: String
    var invoiceName: String?
    var status: String
    var clientName: String
    var clientEmail: String
    var total: String
    var currency: String
    var dueDate: String
    var createdAt: String
    var updatedAt: String

    init(from response: InvoiceResponse) {
        self.serverId = response.id
        self.invoiceNumber = response.invoiceNumber
        self.invoiceName = response.invoiceName
        self.status = response.status
        self.clientName = response.clientName
        self.clientEmail = response.clientEmail
        self.total = response.total
        self.currency = response.currency
        self.dueDate = response.dueDate
        self.createdAt = response.createdAt
        self.updatedAt = response.updatedAt
    }
}
```

Follow same pattern for TimeEntry, Company, User models.

**Commit:**

```bash
git add ios/
git commit -m "feat: add SwiftData cache models and API response structs"
```

---

## Phase 4: iOS App Views

### Task 16: App entry point, TabView, and auth gate

**Files:**
- Create/Modify: `ios/InvoiceKits/InvoiceKits/App/InvoiceKitsApp.swift`
- Create: `ios/InvoiceKits/InvoiceKits/App/AppState.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Auth/LockScreenView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/MainTabView.swift`

`AppState.swift` — central `@Observable` that holds references to all managers.

`InvoiceKitsApp.swift` — checks auth state, shows LockScreenView if Face ID enabled, otherwise MainTabView or auth flow.

`MainTabView.swift` — 4-tab layout (Invoices, Time, Dashboard, Settings).

**Commit:**

```bash
git add ios/
git commit -m "feat: implement app entry, TabView navigation, and Face ID lock screen"
```

---

### Task 17: Auth views (Sign In, Sign Up)

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Auth/SignInView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Auth/SignUpView.swift`

Sign In with Apple button uses `SignInWithAppleButton` from AuthenticationServices. Google uses GoogleSignIn SDK (add via SPM: `https://github.com/google/GoogleSignIn-iOS`). Email form uses native SwiftUI `TextField` and `SecureField`.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement Sign In and Sign Up views with Apple, Google, and email"
```

---

### Task 18: Invoice list and detail views

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/InvoiceListView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/InvoiceDetailView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Components/StatusBadge.swift`

List uses `.searchable()`, `.refreshable {}`, status filter picker, `.swipeActions` for delete/mark paid. Detail shows all invoice fields, action buttons (Send, Mark Paid, PDF, Make Recurring), reminder/late fee toggles, and payment history.

iPad: `NavigationSplitView` with list in sidebar, detail in main area.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement invoice list and detail views with search, filters, swipe actions"
```

---

### Task 19: Invoice form (create/edit) with AI and voice

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/InvoiceFormView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/AIGenerateSection.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/VoiceRecordingView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/ClientRatingBadge.swift`

Form uses native SwiftUI `Form` with sections: Client Info, Line Items (dynamic add/remove), Financial (tax, discount, currency), Template picker, Notes.

AI section: collapsible `DisclosureGroup` with `TextEditor` and Generate button. Voice: `AVAudioRecorder` with visual recording indicator. Client rating: fetches from `/clients/stats/` on email field change (debounced).

**Commit:**

```bash
git add ios/
git commit -m "feat: implement invoice form with AI generate, voice recording, and client rating"
```

---

### Task 20: PDF preview and share

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Invoices/PDFPreviewView.swift`

Uses `PDFKit.PDFView` wrapped in `UIViewRepresentable`. Downloads PDF from API, renders natively. Share button uses `ShareLink` or `UIActivityViewController` for the PDF data.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement PDF preview with PDFKit and native share sheet"
```

---

### Task 21: Time tracking views and timer

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/TimeTracking/TimeEntryListView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/TimeTracking/TimeEntryFormView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/TimeTracking/TimerCardView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/TimeTracking/BillTimeView.swift`

Timer card shows live HH:MM:SS via `TimelineView`. Start/stop/discard buttons. List view with filters. Bill Time shows selectable entries with total.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement time tracking views with live timer, entries, and bill time"
```

---

### Task 22: Live Activities and Dynamic Island for timer

**Files:**
- Create: `ios/InvoiceKits/InvoiceKitsWidgetExtension/TimerLiveActivityBundle.swift`
- Create: `ios/InvoiceKits/InvoiceKitsWidgetExtension/TimerLiveActivityView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Models/TimerActivityAttributes.swift`

Uses `ActivityKit` to start a Live Activity when timer starts. Shows client name, elapsed time, and stop button on lock screen and Dynamic Island.

```swift
import ActivityKit

struct TimerActivityAttributes: ActivityAttributes {
    let clientName: String
    let description: String

    struct ContentState: Codable, Hashable {
        let startedAt: Date
        let isRunning: Bool
    }
}
```

**Commit:**

```bash
git add ios/
git commit -m "feat: implement Live Activities and Dynamic Island for time tracking timer"
```

---

### Task 23: Recurring invoices views

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Recurring/RecurringListView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Recurring/RecurringDetailView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Recurring/RecurringFormView.swift`

List, detail, create/edit following same patterns as invoice views. Toggle active/paused, generate now action.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement recurring invoice views (list, detail, create/edit)"
```

---

### Task 24: Dashboard view

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Dashboard/DashboardView.swift`

Stats cards (total invoices, revenue, outstanding, overdue). Active timer widget. AI generations remaining. Recent invoices list. Uses `ScrollView` with `LazyVGrid` for cards.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement dashboard with stats, timer widget, and recent invoices"
```

---

### Task 25: Settings views

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/SettingsView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/CompanyProfileView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/ReminderSettingsView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/LateFeeSettingsView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/SubscriptionView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/AccountView.swift`
- Create: `ios/InvoiceKits/InvoiceKits/Views/Settings/AppSettingsView.swift`

Settings menu uses `List` with navigation links. Company profile uses `PhotosPicker` for logo/signature. Subscription view shows current plan, IAP options via StoreManager. App settings has Face ID toggle, lock timing, appearance picker.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement settings views (company, reminders, late fees, billing, account, app)"
```

---

### Task 26: Push notification setup

**Files:**
- Create: `ios/InvoiceKits/InvoiceKits/Services/NotificationManager.swift`
- Modify: `ios/InvoiceKits/InvoiceKits/App/InvoiceKitsApp.swift`

Register for APNs, send device token to backend. Handle notification tap to navigate to relevant invoice. Request permission after first invoice created.

**Commit:**

```bash
git add ios/
git commit -m "feat: implement push notification registration and handling"
```

---

## Phase 5: Polish & Submission

### Task 27: App icon and launch screen

**Files:**
- Modify: `ios/InvoiceKits/InvoiceKits/Resources/Assets.xcassets`

Create app icon set (1024x1024 source, Xcode auto-generates sizes). Design launch screen with InvoiceKits logo.

**Commit:**

```bash
git add ios/
git commit -m "feat: add app icon and launch screen"
```

---

### Task 28: Haptics, animations, and polish

**Files:**
- Modify: Various view files

Add `UIImpactFeedbackGenerator` on timer start/stop, invoice status changes, successful saves. Add `.animation()` modifiers for list transitions. Add empty state views for lists.

**Commit:**

```bash
git add ios/
git commit -m "feat: add haptic feedback, animations, and empty state views"
```

---

### Task 29: App Store Connect configuration

**Step 1:** In App Store Connect:
- Create new app: InvoiceKits, bundle ID `com.invoicekits.app`
- Category: Business (primary), Finance (secondary)
- Add subscription group "InvoiceKits Pro" with 4 subscription products
- Add 3 consumable products for credit packs
- Configure App Store Server Notifications V2 URL: `https://www.invoicekits.com/api/v2/billing/apple-notifications/`

**Step 2:** Prepare metadata:
- App name: InvoiceKits
- Subtitle: AI Invoice Generator & Timer
- Description, keywords, screenshots (iPhone + iPad), privacy policy URL
- Privacy Nutrition Labels (see design doc)

**Step 3:** Upload build via Xcode (Product > Archive > Distribute)

**Step 4:** Submit for review

---

### Task 30: Django production deployment for API v2

**Files:**
- Modify: `config/settings/production.py` (add APPLE_CLIENT_ID, CORS for iOS)
- Modify: `railway.json` (ensure migrations run)

**Step 1:** Add environment variables to Railway:
```
APPLE_CLIENT_ID=com.invoicekits.app
```

**Step 2:** Add CORS configuration for iOS app:
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://www.invoicekits.com',
]
# iOS apps don't send Origin headers, so also allow requests without Origin
CORS_ALLOW_CREDENTIALS = True
```

**Step 3:** Deploy and verify API v2 endpoints are accessible.

**Step 4: Commit**

```bash
git add config/
git commit -m "feat: configure production settings for iOS API v2 deployment"
```

---

## Task Dependency Graph

```
Phase 1 (Django Auth)         Phase 3 (Xcode Setup)
  Task 1  ─► Task 2            Task 10 ─► Task 11
  Task 2  ─► Task 3                       Task 12
  Task 3  ─► Task 4, 5                    Task 13
                                           Task 14
Phase 2 (Django Endpoints)                 Task 15
  Task 3  ─► Task 6
  Task 6  ─► Task 7          Phase 4 (Views) — depends on Phase 3
  Task 6  ─► Task 8            Task 15 ─► Task 16
  Task 6  ─► Task 9            Task 16 ─► Task 17-26

Phase 5 (Polish)              Phase 2 + Phase 4 complete
  Task 27-28 ─► Task 29        ─► Task 30
```

**Phases 1-2 (Django) and Phase 3 (Xcode foundation) can run in parallel.**
Phase 4 (iOS views) depends on Phase 3.
Phase 5 depends on everything else.
