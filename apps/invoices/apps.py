"""
App configuration for invoices.
"""
from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoices'
    verbose_name = 'Invoices'

    def ready(self):
        """Import signals when app is ready."""
        from . import signals  # noqa: F401
