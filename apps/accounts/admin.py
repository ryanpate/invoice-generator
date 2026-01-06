"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'email', 'username', 'subscription_tier', 'subscription_status',
        'invoices_created_this_month', 'is_active', 'created_at'
    ]
    list_filter = ['subscription_tier', 'subscription_status', 'is_active', 'is_staff']
    search_fields = ['email', 'username', 'stripe_customer_id']
    ordering = ['-created_at']

    fieldsets = UserAdmin.fieldsets + (
        ('Subscription', {
            'fields': (
                'stripe_customer_id',
                'subscription_tier',
                'subscription_status',
            )
        }),
        ('API', {
            'fields': (
                'api_key',
                'api_key_created_at',
            )
        }),
        ('Usage', {
            'fields': (
                'invoices_created_this_month',
                'api_calls_this_month',
                'usage_reset_date',
            )
        }),
    )

    readonly_fields = ['api_key', 'api_key_created_at', 'created_at', 'updated_at']
