from django.urls import path, include

from apps.api_v2.views.invoices import dashboard_stats_view

app_name = 'api_v2'

urlpatterns = [
    path('auth/', include('apps.api_v2.urls_auth')),
    path('invoices/', include('apps.api_v2.urls_invoices')),
    path('ai/', include('apps.api_v2.urls_ai')),
    path('time/', include('apps.api_v2.urls_time')),
    path('recurring/', include('apps.api_v2.urls_recurring')),
    path('company/', include('apps.api_v2.urls_company')),
    path('settings/', include('apps.api_v2.urls_settings')),
    path('billing/', include('apps.api_v2.urls_billing')),
    path('clients/', include('apps.api_v2.urls_clients')),
    path('dashboard/stats/', dashboard_stats_view, name='api_v2_dashboard_stats'),
]
