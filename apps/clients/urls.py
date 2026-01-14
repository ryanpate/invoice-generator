"""
URL configuration for Client Portal.
"""
from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    # Authentication
    path('portal/request-access/', views.RequestAccessView.as_view(), name='request_access'),
    path('portal/check-email/', views.CheckEmailView.as_view(), name='check_email'),
    path('portal/auth/<str:token>/', views.MagicLinkAuthView.as_view(), name='magic_link_auth'),
    path('portal/logout/', views.LogoutView.as_view(), name='logout'),

    # Portal Dashboard
    path('portal/', views.DashboardView.as_view(), name='dashboard'),

    # Invoices
    path('portal/invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('portal/invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('portal/invoices/<int:pk>/pay/', views.InitiatePaymentView.as_view(), name='initiate_payment'),
    path('portal/invoices/<int:pk>/payment-success/', views.PaymentSuccessView.as_view(), name='payment_success'),

    # Payments
    path('portal/payments/', views.PaymentHistoryView.as_view(), name='payment_history'),

    # Statement
    path('portal/statement/', views.DownloadStatementView.as_view(), name='download_statement'),
]
