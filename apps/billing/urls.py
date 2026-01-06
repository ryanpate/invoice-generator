"""
URL patterns for billing app.
"""
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.BillingOverviewView.as_view(), name='overview'),
    path('plans/', views.PlansView.as_view(), name='plans'),
    path('checkout/<str:plan>/', views.create_checkout_session, name='checkout'),
    path('portal/', views.customer_portal, name='portal'),
    path('success/', views.CheckoutSuccessView.as_view(), name='success'),
    path('cancel/', views.CheckoutCancelView.as_view(), name='cancel'),
    path('webhook/', views.stripe_webhook, name='webhook'),
]
