"""
URL configuration for API v2 company profile endpoints.
"""
from django.urls import path

from apps.api_v2.views.company import (
    company_detail,
    upload_logo,
    remove_logo,
    upload_signature,
    remove_signature,
)

urlpatterns = [
    path('', company_detail, name='api_v2_company_detail'),
    path('logo/', upload_logo, name='api_v2_company_upload_logo'),
    path('logo/remove/', remove_logo, name='api_v2_company_remove_logo'),
    path('signature/', upload_signature, name='api_v2_company_upload_signature'),
    path('signature/remove/', remove_signature, name='api_v2_company_remove_signature'),
]
