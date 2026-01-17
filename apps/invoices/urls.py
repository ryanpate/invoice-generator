"""
URL patterns for authenticated invoices app pages (no i18n).
"""
from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # Invoice CRUD
    path('', views.InvoiceListView.as_view(), name='list'),
    path('create/', views.InvoiceCreateView.as_view(), name='create'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='delete'),
    path('<int:pk>/send/', views.InvoiceSendEmailView.as_view(), name='send_email'),

    # PDF generation
    path('<int:pk>/pdf/', views.generate_pdf, name='generate_pdf'),
    path('<int:pk>/download/', views.download_pdf, name='download_pdf'),

    # Status updates
    path('<int:pk>/status/<str:status>/', views.mark_invoice_status, name='mark_status'),
    path('<int:pk>/toggle-reminders/', views.toggle_invoice_reminders, name='toggle_reminders'),
    path('<int:pk>/toggle-late-fees/', views.toggle_invoice_late_fees, name='toggle_late_fees'),

    # Client analytics
    path('client-stats/', views.client_payment_stats, name='client_payment_stats'),

    # AI Invoice Generator
    path('ai-generate/', views.ai_generate_line_items, name='ai_generate_line_items'),

    # Batch processing
    path('batch/', views.BatchUploadView.as_view(), name='batch_upload'),
    path('batch/<int:pk>/', views.BatchResultView.as_view(), name='batch_result'),
    path('batch/<int:pk>/download/', views.download_batch_zip, name='batch_download'),
    path('batch/template/', views.download_csv_template, name='csv_template'),

    # Recurring invoices
    path('recurring/', views.RecurringInvoiceListView.as_view(), name='recurring_list'),
    path('recurring/create/', views.RecurringInvoiceCreateView.as_view(), name='recurring_create'),
    path('recurring/<int:pk>/', views.RecurringInvoiceDetailView.as_view(), name='recurring_detail'),
    path('recurring/<int:pk>/edit/', views.RecurringInvoiceUpdateView.as_view(), name='recurring_edit'),
    path('recurring/<int:pk>/delete/', views.RecurringInvoiceDeleteView.as_view(), name='recurring_delete'),
    path('recurring/<int:pk>/toggle-status/', views.recurring_toggle_status, name='recurring_toggle_status'),
    path('recurring/<int:pk>/generate-now/', views.recurring_generate_now, name='recurring_generate_now'),

    # Convert invoice to recurring
    path('<int:pk>/make-recurring/', views.convert_to_recurring, name='convert_to_recurring'),

    # Public invoice views (for QR code links - no auth required, but use UUID so no i18n needed)
    path('invoice/<uuid:token>/', views.PublicInvoiceView.as_view(), name='public_invoice'),
    path('invoice/<uuid:token>/mark-paid/', views.PublicInvoiceMarkPaidView.as_view(), name='public_mark_paid'),
    path('invoice/<uuid:token>/pdf/', views.public_invoice_pdf, name='public_invoice_pdf'),

    # Time Tracking
    path('time/', views.TimeEntryListView.as_view(), name='time_list'),
    path('time/create/', views.TimeEntryCreateView.as_view(), name='time_create'),
    path('time/<int:pk>/edit/', views.TimeEntryUpdateView.as_view(), name='time_edit'),
    path('time/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='time_delete'),
    path('time/bill/', views.BillTimeView.as_view(), name='bill_time'),

    # Timer AJAX endpoints
    path('timer/start/', views.timer_start, name='timer_start'),
    path('timer/<int:timer_id>/stop/', views.timer_stop, name='timer_stop'),
    path('timer/<int:timer_id>/discard/', views.timer_discard, name='timer_discard'),
    path('timer/status/', views.timer_status, name='timer_status'),
]
