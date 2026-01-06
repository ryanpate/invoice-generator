"""
URL patterns for API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')

app_name = 'api'

urlpatterns = [
    path('', views.api_info, name='info'),
    path('', include(router.urls)),
    path('templates/', views.TemplateListView.as_view(), name='templates'),
    path('usage/', views.UsageView.as_view(), name='usage'),
]
