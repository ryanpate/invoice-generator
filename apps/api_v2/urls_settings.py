"""
URL configuration for API v2 settings endpoints (reminders and late fees).
"""
from django.urls import path

from apps.api_v2.views.settings import reminder_settings, late_fee_settings

urlpatterns = [
    path('reminders/', reminder_settings, name='api_v2_reminder_settings'),
    path('late-fees/', late_fee_settings, name='api_v2_late_fee_settings'),
]
