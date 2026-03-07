"""
URL configuration for API v2 invoice endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api_v2.views.invoices import InvoiceV2ViewSet

router = DefaultRouter()
router.register(r'', InvoiceV2ViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
