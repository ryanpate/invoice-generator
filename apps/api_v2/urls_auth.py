from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from apps.api_v2.views.auth import (
    register_view,
    login_view,
    apple_social_auth_view,
    google_social_auth_view,
    delete_account_view,
    profile_view,
)

urlpatterns = [
    path('register/', register_view, name='auth-register'),
    path('login/', login_view, name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('social/apple/', apple_social_auth_view, name='auth-social-apple'),
    path('social/google/', google_social_auth_view, name='auth-social-google'),
    path('account/', delete_account_view, name='auth-delete-account'),
    path('profile/', profile_view, name='auth-profile'),
]
