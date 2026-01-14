"""
Admin configuration for billing app.
"""
from django.contrib import admin
from .models import UsageRecord, PaymentHistory, CreditPurchase, TemplatePurchase


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'invoices_created', 'api_calls', 'batch_uploads']
    list_filter = ['month']
    search_fields = ['user__email']


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['user__email', 'stripe_payment_intent_id', 'stripe_invoice_id']
    readonly_fields = ['created_at']


@admin.register(CreditPurchase)
class CreditPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'pack_id', 'credits_amount', 'price_paid', 'status', 'created_at']
    list_filter = ['status', 'pack_id', 'created_at']
    search_fields = ['user__email', 'stripe_session_id', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']


@admin.register(TemplatePurchase)
class TemplatePurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'template_id', 'is_bundle', 'price_paid', 'status', 'created_at']
    list_filter = ['status', 'is_bundle', 'template_id', 'created_at']
    search_fields = ['user__email', 'stripe_session_id', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
