"""
URL configuration for API v2 client analytics endpoints.
"""
from django.urls import path

from apps.api_v2.views.clients import client_stats

urlpatterns = [
    path('stats/', client_stats, name='api_v2_client_stats'),
]
