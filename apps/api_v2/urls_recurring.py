"""
URL configuration for API v2 recurring invoice endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api_v2.views.recurring import RecurringInvoiceV2ViewSet

router = DefaultRouter()
router.register(r'', RecurringInvoiceV2ViewSet, basename='recurring')

urlpatterns = [
    path('', include(router.urls)),
]
