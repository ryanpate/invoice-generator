"""
Admin configuration for companies app.
"""
from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'email', 'default_currency', 'created_at']
    list_filter = ['default_currency', 'country']
    search_fields = ['name', 'user__email', 'email']
    readonly_fields = ['created_at', 'updated_at']
