"""
Admin configuration for Client Portal models.
"""
from django.contrib import admin
from .models import Client, MagicLinkToken, ClientSession, ClientPayment


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'last_accessed_at', 'created_at']
    search_fields = ['email', 'name', 'preferred_name']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(admin.ModelAdmin):
    list_display = ['client', 'token_preview', 'created_at', 'expires_at', 'used_at']
    search_fields = ['client__email', 'token']
    list_filter = ['created_at', 'used_at']
    readonly_fields = ['token', 'created_at']
    raw_id_fields = ['client', 'invoice']

    def token_preview(self, obj):
        return f"{obj.token[:12]}..."
    token_preview.short_description = 'Token'


@admin.register(ClientSession)
class ClientSessionAdmin(admin.ModelAdmin):
    list_display = ['client', 'session_preview', 'is_active', 'created_at', 'expires_at', 'last_activity']
    search_fields = ['client__email', 'session_token']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['session_token', 'created_at']
    raw_id_fields = ['client', 'magic_link_token']
    actions = ['invalidate_sessions']

    def session_preview(self, obj):
        return f"{obj.session_token[:12]}..."
    session_preview.short_description = 'Session'

    def invalidate_sessions(self, request, queryset):
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'Invalidated {count} sessions.')
    invalidate_sessions.short_description = 'Invalidate selected sessions'


@admin.register(ClientPayment)
class ClientPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'invoice', 'amount', 'currency', 'status', 'created_at', 'completed_at']
    search_fields = ['client__email', 'invoice__invoice_number', 'stripe_checkout_session_id', 'stripe_payment_intent_id']
    list_filter = ['status', 'currency', 'created_at']
    readonly_fields = ['stripe_checkout_session_id', 'stripe_payment_intent_id', 'stripe_transfer_id', 'created_at', 'completed_at']
    raw_id_fields = ['client', 'invoice']
