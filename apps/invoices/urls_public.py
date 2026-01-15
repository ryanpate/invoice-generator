"""
URL patterns for public invoices app pages (with i18n support).
These URLs are NOT namespaced - they're included directly in i18n_patterns.
"""
from django.urls import path
from . import views

# No app_name - these are root-level URLs to avoid namespace conflict with invoices app
# app_name = 'invoices'

urlpatterns = [
    # Landing page is now defined directly in config/urls.py
    # path('', views.LandingPageView.as_view(), name='landing'),
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
]
