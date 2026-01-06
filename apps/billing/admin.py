"""
Admin configuration for billing app.
"""
from django.contrib import admin
from .models import UsageRecord, PaymentHistory


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
