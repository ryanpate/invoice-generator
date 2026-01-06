"""
URL patterns for accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('settings/', views.AccountSettingsView.as_view(), name='settings'),
    path('api-key/generate/', views.generate_api_key, name='generate_api_key'),
    path('delete/', views.delete_account, name='delete_account'),
]
