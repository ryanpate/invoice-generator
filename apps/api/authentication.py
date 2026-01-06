"""
API Key authentication for REST API.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.accounts.models import CustomUser


class APIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication using API keys.

    Usage: Include header 'X-API-Key: inv_your_api_key_here'
    """

    keyword = 'X-API-Key'

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None  # No API key provided, try other auth methods

        try:
            user = CustomUser.objects.get(api_key=api_key)
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')

        if not user.is_active:
            raise AuthenticationFailed('User account is disabled')

        if not user.has_api_access():
            raise AuthenticationFailed('API access not available on your plan')

        # Check API call limit
        if not user.can_make_api_call():
            raise AuthenticationFailed('API call limit exceeded for this month')

        # Increment API call counter
        user.increment_api_call_count()

        return (user, None)

    def authenticate_header(self, request):
        return self.keyword
