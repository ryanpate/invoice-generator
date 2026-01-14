"""
URL patterns for invoices app.
"""
from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # Landing pages
    path('', views.LandingPageView.as_view(), name='landing'),
    path('pricing/', views.PricingPageView.as_view(), name='pricing'),
    path('for-freelancers/', views.FreelancersLandingPageView.as_view(), name='for_freelancers'),
    path('for-small-business/', views.SmallBusinessLandingPageView.as_view(), name='for_small_business'),
    path('for-consultants/', views.ConsultantsLandingPageView.as_view(), name='for_consultants'),
    path('compare/', views.CompareLandingPageView.as_view(), name='compare'),

    # Template showcase pages
    path('templates/clean-slate/', views.CleanSlateShowcaseView.as_view(), name='template_clean_slate'),
    path('templates/executive/', views.ExecutiveShowcaseView.as_view(), name='template_executive'),
    path('templates/bold-modern/', views.BoldModernShowcaseView.as_view(), name='template_bold_modern'),
    path('templates/classic-professional/', views.ClassicProfessionalShowcaseView.as_view(), name='template_classic_professional'),
    path('templates/neon-edge/', views.NeonEdgeShowcaseView.as_view(), name='template_neon_edge'),

    # Free tools (SEO pages - no auth required)
    path('tools/invoice-calculator/', views.InvoiceCalculatorView.as_view(), name='invoice_calculator'),
    path('tools/late-fee-calculator/', views.LateFeeCalculatorView.as_view(), name='late_fee_calculator'),

    # Invoice CRUD
    path('invoices/', views.InvoiceListView.as_view(), name='list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='edit'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='delete'),
    path('invoices/<int:pk>/send/', views.InvoiceSendEmailView.as_view(), name='send_email'),

    # PDF generation
    path('invoices/<int:pk>/pdf/', views.generate_pdf, name='generate_pdf'),
    path('invoices/<int:pk>/download/', views.download_pdf, name='download_pdf'),

    # Status updates
    path('invoices/<int:pk>/status/<str:status>/', views.mark_invoice_status, name='mark_status'),

    # Batch processing
    path('invoices/batch/', views.BatchUploadView.as_view(), name='batch_upload'),
    path('invoices/batch/<int:pk>/', views.BatchResultView.as_view(), name='batch_result'),
    path('invoices/batch/<int:pk>/download/', views.download_batch_zip, name='batch_download'),
    path('invoices/batch/template/', views.download_csv_template, name='csv_template'),

    # Recurring invoices
    path('invoices/recurring/', views.RecurringInvoiceListView.as_view(), name='recurring_list'),
    path('invoices/recurring/create/', views.RecurringInvoiceCreateView.as_view(), name='recurring_create'),
    path('invoices/recurring/<int:pk>/', views.RecurringInvoiceDetailView.as_view(), name='recurring_detail'),
    path('invoices/recurring/<int:pk>/edit/', views.RecurringInvoiceUpdateView.as_view(), name='recurring_edit'),
    path('invoices/recurring/<int:pk>/delete/', views.RecurringInvoiceDeleteView.as_view(), name='recurring_delete'),
    path('invoices/recurring/<int:pk>/toggle-status/', views.recurring_toggle_status, name='recurring_toggle_status'),
    path('invoices/recurring/<int:pk>/generate-now/', views.recurring_generate_now, name='recurring_generate_now'),

    # Public invoice views (for QR code links - no auth required)
    path('invoice/<uuid:token>/', views.PublicInvoiceView.as_view(), name='public_invoice'),
    path('invoice/<uuid:token>/mark-paid/', views.PublicInvoiceMarkPaidView.as_view(), name='public_mark_paid'),
    path('invoice/<uuid:token>/pdf/', views.public_invoice_pdf, name='public_invoice_pdf'),
]
