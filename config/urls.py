"""
URL configuration for Invoice Generator Pro.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for Railway."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health_check, name='health_check'),
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
