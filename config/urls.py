"""
URL configuration for Invoice Generator Pro.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap

from apps.blog.sitemaps import BlogPostSitemap
from apps.companies.views import AcceptInvitationView
from apps.invoices.views import LandingPageView
from apps.affiliates.views import referral_redirect


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            '/', '/pricing/', '/for-freelancers/', '/for-small-business/', '/for-consultants/', '/compare/',
            '/contact/', '/help/', '/privacy/', '/terms/', '/api/docs/', '/blog/',
            '/templates/clean-slate/', '/templates/executive/', '/templates/bold-modern/',
            '/templates/classic-professional/', '/templates/neon-edge/',
            '/tools/invoice-calculator/', '/tools/late-fee-calculator/',
            '/features/ai-invoice-generator/', '/features/time-tracking/',
            '/affiliate/program/',
        ]

    def location(self, item):
        return item


sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
}


def health_check(request):
    """Simple health check endpoint for Railway."""
    return JsonResponse({'status': 'ok'})


def bing_site_auth(request):
    """Serve Bing Webmaster Tools verification file."""
    content = """<?xml version="1.0"?>
<users>
	<user>29ACAC7E27CA9CB577CE5708757F488A</user>
</users>
"""
    return HttpResponse(content, content_type='application/xml')


def service_worker(request):
    """Serve service worker from root URL for proper scope."""
    import os
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'service-worker.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def robots_txt(request):
    content = """# InvoiceKits robots.txt
# https://www.invoicekits.com

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/
Disallow: /api/
Disallow: /dashboard/
Disallow: /settings/
Disallow: /billing/
Disallow: /invoices/
Disallow: /portal/

# Allow search engines to crawl public pages
Allow: /$
Allow: /pricing/
Allow: /for-freelancers/
Allow: /for-small-business/
Allow: /for-consultants/
Allow: /compare/
Allow: /contact/
Allow: /help/
Allow: /privacy/
Allow: /terms/
Allow: /api/docs/
Allow: /blog/
Allow: /templates/
Allow: /tools/
Allow: /features/
Allow: /affiliate/program/
Allow: /portal/request-access/

# Allow internationalized versions
Allow: /es/
Allow: /fr/

# Sitemap location
Sitemap: https://www.invoicekits.com/sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')


def ads_txt(request):
    """Serve ads.txt for Google AdSense verification."""
    content = """google.com, pub-5523870768931777, DIRECT, f08c47fec0942fa0
"""
    return HttpResponse(content, content_type='text/plain')


# Non-internationalized URLs (system, admin, authenticated routes)
urlpatterns = [
    # System endpoints
    path('health/', health_check, name='health_check'),

    path('robots.txt', robots_txt, name='robots_txt'),
    path('ads.txt', ads_txt, name='ads_txt'),
    path('BingSiteAuth.xml', bing_site_auth, name='bing_site_auth'),
    path('service-worker.js', service_worker, name='service_worker'),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include('allauth.urls')),

    # Authenticated app routes (English only)
    path('invoices/', include('apps.invoices.urls')),
    path('', include('apps.clients.urls')),  # Client Portal at /portal/
    path('dashboard/', include('apps.accounts.urls')),
    path('billing/', include('apps.billing.urls')),
    path('settings/', include('apps.companies.urls')),

    # API
    path('api/v1/', include('apps.api.urls')),

    # Affiliate Program
    path('affiliate/', include('apps.affiliates.urls')),

    # Referral redirect (short link for affiliates)
    path('ref/<str:code>/', referral_redirect, name='referral_redirect'),

    # Team invitation acceptance (public URL with UUID, no i18n needed)
    path('invitation/<uuid:token>/', AcceptInvitationView.as_view(), name='accept_invitation'),

    # Language switcher endpoint
    path('i18n/', include('django.conf.urls.i18n')),
]

# Internationalized URLs (public pages - supports /es/, /fr/ prefixes)
urlpatterns += i18n_patterns(
    # Landing page - explicit pattern to ensure 'landing' URL name is available
    path('', LandingPageView.as_view(), name='landing'),

    # Public invoice pages (pricing, templates, tools - landing handled above)
    path('', include('apps.invoices.urls_public')),

    # Blog
    path('blog/', include('apps.blog.urls')),

    # Static footer pages
    path('contact/', TemplateView.as_view(template_name='pages/contact.html'), name='contact'),
    path('help/', TemplateView.as_view(template_name='pages/help.html'), name='help'),
    path('privacy/', TemplateView.as_view(template_name='pages/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='pages/terms.html'), name='terms'),
    path('api/docs/', TemplateView.as_view(template_name='pages/api_docs.html'), name='api_docs'),

    # Don't prefix English URLs (/ stays as /, not /en/)
    prefix_default_language=False,
)

# Stripe webhooks - only if djstripe is installed
if 'djstripe' in settings.INSTALLED_APPS:
    urlpatterns.append(path('stripe/', include('djstripe.urls', namespace='djstripe')))

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
