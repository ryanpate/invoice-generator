"""
URL configuration for API v2 billing endpoints.
"""
from django.urls import path

from apps.api_v2.views.billing import (
    usage_view,
    entitlements_view,
    verify_apple_receipt,
    register_device,
    apple_server_notification,
)

urlpatterns = [
    path('usage/', usage_view, name='api_v2_billing_usage'),
    path('entitlements/', entitlements_view, name='api_v2_billing_entitlements'),
    path('apple/verify-receipt/', verify_apple_receipt, name='api_v2_apple_verify_receipt'),
    path('device/register/', register_device, name='api_v2_device_register'),
    path('apple/notifications/', apple_server_notification, name='api_v2_apple_notifications'),
]
