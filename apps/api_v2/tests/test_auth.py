"""
Tests for API v2 auth endpoints.

Covers:
- Registration: valid, mismatched passwords, duplicate email
- Login: valid credentials, invalid credentials
- Token refresh: valid refresh token
- Apple social auth: invalid token returns 400
- Google social auth: invalid token returns 400
- Account delete: unauthenticated returns 401, authenticated deletes user
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser


REGISTER_URL = '/api/v2/auth/register/'
LOGIN_URL = '/api/v2/auth/login/'
REFRESH_URL = '/api/v2/auth/token/refresh/'
APPLE_URL = '/api/v2/auth/social/apple/'
GOOGLE_URL = '/api/v2/auth/social/google/'
ACCOUNT_URL = '/api/v2/auth/account/'


def make_user(email='test@example.com', password='securepass123'):
    return CustomUser.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password=password,
    )


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_valid_returns_tokens(self):
        payload = {
            'email': 'newuser@example.com',
            'password': 'strongpass1',
            'password_confirm': 'strongpass1',
        }
        response = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'newuser@example.com')
        self.assertEqual(data['user']['subscription_tier'], 'free')
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_register_email_lowercased(self):
        payload = {
            'email': 'MixedCase@Example.COM',
            'password': 'strongpass1',
            'password_confirm': 'strongpass1',
        }
        response = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(CustomUser.objects.filter(email='mixedcase@example.com').exists())

    def test_register_mismatched_passwords_returns_400(self):
        payload = {
            'email': 'user2@example.com',
            'password': 'strongpass1',
            'password_confirm': 'differentpass',
        }
        response = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirm', response.json())

    def test_register_password_too_short_returns_400(self):
        payload = {
            'email': 'user3@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }
        response = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_email_returns_400(self):
        make_user(email='existing@example.com')
        payload = {
            'email': 'existing@example.com',
            'password': 'strongpass1',
            'password_confirm': 'strongpass1',
        }
        response = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn('email', body)
        self.assertIn('already exists', str(body['email']))

    def test_register_missing_fields_returns_400(self):
        response = self.client.post(REGISTER_URL, {'email': 'x@x.com'}, format='json')
        self.assertEqual(response.status_code, 400)


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email='login@example.com', password='correctpass1')

    def test_login_valid_credentials_returns_tokens(self):
        payload = {'email': 'login@example.com', 'password': 'correctpass1'}
        response = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['email'], 'login@example.com')

    def test_login_invalid_password_returns_400(self):
        payload = {'email': 'login@example.com', 'password': 'wrongpassword'}
        response = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.json())

    def test_login_nonexistent_email_returns_400(self):
        payload = {'email': 'nobody@example.com', 'password': 'correctpass1'}
        response = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)

    def test_login_inactive_user_returns_400(self):
        self.user.is_active = False
        self.user.save()
        payload = {'email': 'login@example.com', 'password': 'correctpass1'}
        response = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(LOGIN_URL, {'email': 'login@example.com'}, format='json')
        self.assertEqual(response.status_code, 400)


class TokenRefreshViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email='refresh@example.com', password='testpass123')

    def test_refresh_valid_token_returns_new_access(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(
            REFRESH_URL, {'refresh': str(refresh)}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())

    def test_refresh_invalid_token_returns_401(self):
        response = self.client.post(
            REFRESH_URL, {'refresh': 'not.a.valid.token'}, format='json'
        )
        self.assertIn(response.status_code, [400, 401])

    def test_refresh_missing_token_returns_400(self):
        response = self.client.post(REFRESH_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)


class AppleSocialAuthViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_apple_invalid_token_returns_400(self):
        """Any non-verifiable Apple id_token must return 400."""
        payload = {'id_token': 'invalid.apple.token'}
        response = self.client.post(APPLE_URL, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_apple_missing_id_token_returns_400(self):
        response = self.client.post(APPLE_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)

    @patch('apps.api_v2.views.auth.requests.get')
    @patch('apps.api_v2.views.auth.jwt.get_unverified_header')
    @patch('apps.api_v2.views.auth.jwt.decode')
    def test_apple_valid_token_new_user_returns_201(self, mock_decode, mock_header, mock_get):
        """Simulate a valid Apple token that decodes successfully."""
        kid = 'test-key-id'
        mock_header.return_value = {'kid': kid}
        mock_get.return_value = MagicMock(
            json=lambda: {'keys': [{'kid': kid, 'kty': 'RSA', 'n': 'n', 'e': 'e'}]}
        )
        mock_decode.return_value = {
            'email': 'appleuser@privaterelay.appleid.com',
            'sub': 'apple-sub-123',
        }

        with patch('apps.api_v2.views.auth.jwt.algorithms.RSAAlgorithm.from_jwk', return_value='mock-key'):
            response = self.client.post(
                APPLE_URL,
                {'id_token': 'valid.apple.token', 'first_name': 'Apple', 'last_name': 'User'},
                format='json',
            )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['email'], 'appleuser@privaterelay.appleid.com')

    @patch('apps.api_v2.views.auth.requests.get')
    @patch('apps.api_v2.views.auth.jwt.get_unverified_header')
    @patch('apps.api_v2.views.auth.jwt.decode')
    def test_apple_valid_token_existing_user_returns_200(self, mock_decode, mock_header, mock_get):
        """Existing Apple-authed user gets 200, not 201."""
        kid = 'test-key-id'
        email = 'existing-apple@example.com'
        make_user(email=email)

        mock_header.return_value = {'kid': kid}
        mock_get.return_value = MagicMock(
            json=lambda: {'keys': [{'kid': kid, 'kty': 'RSA', 'n': 'n', 'e': 'e'}]}
        )
        mock_decode.return_value = {'email': email, 'sub': 'apple-sub-456'}

        with patch('apps.api_v2.views.auth.jwt.algorithms.RSAAlgorithm.from_jwk', return_value='mock-key'):
            response = self.client.post(
                APPLE_URL,
                {'id_token': 'valid.apple.token'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)


class GoogleSocialAuthViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_google_invalid_token_returns_400(self):
        """Google tokeninfo endpoint returning non-200 must yield 400."""
        with patch('apps.api_v2.views.auth.requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=400, json=lambda: {'error': 'bad token'})
            response = self.client.post(GOOGLE_URL, {'id_token': 'bad-token'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_google_missing_id_token_returns_400(self):
        response = self.client.post(GOOGLE_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)

    @patch('apps.api_v2.views.auth.requests.get')
    def test_google_valid_token_new_user_returns_201(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'email': 'googleuser@gmail.com',
                'given_name': 'Google',
                'family_name': 'User',
            },
        )
        response = self.client.post(GOOGLE_URL, {'id_token': 'valid-google-token'}, format='json')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['email'], 'googleuser@gmail.com')
        user = CustomUser.objects.get(email='googleuser@gmail.com')
        self.assertEqual(user.first_name, 'Google')
        self.assertEqual(user.last_name, 'User')

    @patch('apps.api_v2.views.auth.requests.get')
    def test_google_valid_token_existing_user_returns_200(self, mock_get):
        email = 'existing-google@example.com'
        make_user(email=email)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'email': email, 'given_name': 'Google', 'family_name': 'User'},
        )
        response = self.client.post(GOOGLE_URL, {'id_token': 'valid-google-token'}, format='json')

        self.assertEqual(response.status_code, 200)

    @patch('apps.api_v2.views.auth.requests.get')
    def test_google_payload_missing_email_returns_400(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'given_name': 'No', 'family_name': 'Email'},
        )
        response = self.client.post(GOOGLE_URL, {'id_token': 'valid-google-token'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())


class DeleteAccountViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_delete_returns_401(self):
        # DRF returns 401 for JWT-only requests and 403 when SessionAuthentication
        # is also present (CSRF enforcement). Both correctly deny unauthenticated access.
        response = self.client.delete(ACCOUNT_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_authenticated_delete_removes_user_and_returns_204(self):
        user = make_user(email='tobedeleted@example.com', password='deletepass1')
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        response = self.client.delete(ACCOUNT_URL)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CustomUser.objects.filter(email='tobedeleted@example.com').exists())
