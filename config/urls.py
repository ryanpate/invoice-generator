"""
URL configuration for Invoice Generator Pro.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['/', '/pricing/']

    def location(self, item):
        return item


sitemaps = {
    'static': StaticViewSitemap,
}


def health_check(request):
    """Simple health check endpoint for Railway."""
    return JsonResponse({'status': 'ok'})


def robots_txt(request):
    """Serve robots.txt from root URL."""
    content = """# InvoiceKits robots.txt
# https://invoicekits.com

User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/
Disallow: /api/
Disallow: /dashboard/
Disallow: /settings/
Disallow: /billing/
Disallow: /invoices/

# Allow search engines to crawl public pages
Allow: /$
Allow: /pricing/

# Sitemap location
Sitemap: https://invoicekits.com/sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include('allauth.urls')),

    # Main app URLs
    path('', include('apps.invoices.urls')),
    path('dashboard/', include('apps.accounts.urls')),
    path('billing/', include('apps.billing.urls')),
    path('settings/', include('apps.companies.urls')),

    # API
    path('api/v1/', include('apps.api.urls')),
]

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
