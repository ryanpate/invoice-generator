"""
URL patterns for accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('settings/', views.AccountSettingsView.as_view(), name='settings'),
    path('settings/update-profile/', views.update_profile, name='update_profile'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/update-preferences/', views.update_preferences, name='update_preferences'),
    path('api-key/generate/', views.generate_api_key, name='generate_api_key'),
    path('api-key/regenerate/', views.regenerate_api_key, name='regenerate_api_key'),
    path('delete/', views.delete_account, name='delete_account'),
]
