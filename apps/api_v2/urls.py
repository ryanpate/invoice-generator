from django.urls import path, include

app_name = 'api_v2'

urlpatterns = [
    path('auth/', include('apps.api_v2.urls_auth')),
    path('invoices/', include('apps.api_v2.urls_invoices')),
    path('ai/', include('apps.api_v2.urls_ai')),
    path('time/', include('apps.api_v2.urls_time')),
]
