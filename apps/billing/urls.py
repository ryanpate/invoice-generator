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

    # Credit purchase routes
    path('credits/', views.CreditsView.as_view(), name='credits'),
    path('credits/purchase/<str:pack_id>/', views.purchase_credits, name='purchase_credits'),
    path('credits/success/', views.CreditPurchaseSuccessView.as_view(), name='credits_success'),

    # Stripe Connect routes (for receiving client payments)
    path('stripe-connect/', views.StripeConnectStatusView.as_view(), name='stripe_connect_status'),
    path('stripe-connect/start/', views.stripe_connect_start, name='stripe_connect_start'),
    path('stripe-connect/return/', views.stripe_connect_return, name='stripe_connect_return'),
    path('stripe-connect/refresh/', views.stripe_connect_refresh, name='stripe_connect_refresh'),
    path('stripe-connect/dashboard/', views.stripe_connect_dashboard, name='stripe_connect_dashboard'),
    path('stripe-connect/disconnect/', views.stripe_connect_disconnect, name='stripe_connect_disconnect'),
]
