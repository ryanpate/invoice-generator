"""
URL patterns for companies app.
"""
from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('company/', views.CompanySettingsView.as_view(), name='settings'),
    path('company/remove-logo/', views.remove_logo, name='remove_logo'),
    path('company/remove-signature/', views.remove_signature, name='remove_signature'),
]
