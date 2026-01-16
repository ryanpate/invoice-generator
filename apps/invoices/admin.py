"""
Admin configuration for invoices app.
"""
from django.contrib import admin
from .models import (
    Invoice, LineItem, InvoiceBatch, RecurringInvoice, RecurringLineItem,
    PaymentReminderSettings, PaymentReminderLog
)


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 1
    fields = ['description', 'quantity', 'rate', 'amount']
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'client_name', 'company', 'status',
        'total', 'currency', 'due_date', 'created_at'
    ]
    list_filter = ['status', 'currency', 'template_style', 'created_at']
    search_fields = ['invoice_number', 'client_name', 'client_email']
    readonly_fields = ['subtotal', 'tax_amount', 'total', 'created_at', 'updated_at']
    inlines = [LineItemInline]

    fieldsets = (
        ('Invoice Details', {
            'fields': ('company', 'invoice_number', 'status')
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_email', 'client_phone', 'client_address')
        }),
        ('Dates & Terms', {
            'fields': ('invoice_date', 'due_date', 'payment_terms')
        }),
        ('Financial', {
            'fields': ('currency', 'subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total')
        }),
        ('Additional', {
            'fields': ('notes', 'template_style', 'pdf_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoiceBatch)
class InvoiceBatchAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'company', 'status', 'total_invoices',
        'processed_invoices', 'failed_invoices', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'completed_at']


class RecurringLineItemInline(admin.TabularInline):
    model = RecurringLineItem
    extra = 1
    fields = ['description', 'quantity', 'rate', 'order']


@admin.register(RecurringInvoice)
class RecurringInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'client_name', 'company', 'frequency', 'status',
        'next_run_date', 'invoices_generated', 'created_at'
    ]
    list_filter = ['status', 'frequency', 'currency', 'created_at']
    search_fields = ['name', 'client_name', 'client_email']
    readonly_fields = [
        'invoices_generated', 'last_generated_at', 'last_invoice',
        'created_at', 'updated_at'
    ]
    inlines = [RecurringLineItemInline]
    date_hierarchy = 'next_run_date'

    fieldsets = (
        ('Recurring Invoice Details', {
            'fields': ('company', 'name', 'status')
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_email', 'client_phone', 'client_address')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_run_date')
        }),
        ('Invoice Settings', {
            'fields': ('currency', 'payment_terms', 'tax_rate', 'template_style', 'notes')
        }),
        ('Notifications', {
            'fields': ('send_email_on_generation', 'auto_send_to_client')
        }),
        ('Statistics', {
            'fields': ('invoices_generated', 'last_generated_at', 'last_invoice'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['pause_recurring', 'resume_recurring']

    @admin.action(description='Pause selected recurring invoices')
    def pause_recurring(self, request, queryset):
        updated = queryset.filter(status='active').update(status='paused')
        self.message_user(request, f'{updated} recurring invoice(s) paused.')

    @admin.action(description='Resume selected recurring invoices')
    def resume_recurring(self, request, queryset):
        updated = queryset.filter(status='paused').update(status='active')
        self.message_user(request, f'{updated} recurring invoice(s) resumed.')


@admin.register(PaymentReminderSettings)
class PaymentReminderSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'reminders_enabled', 'cc_business_owner',
        'remind_3_days_before', 'remind_on_due_date', 'remind_7_days_after'
    ]
    list_filter = ['reminders_enabled', 'cc_business_owner']
    search_fields = ['company__name']

    fieldsets = (
        ('Company', {
            'fields': ('company',)
        }),
        ('Status', {
            'fields': ('reminders_enabled', 'cc_business_owner')
        }),
        ('Before Due Date', {
            'fields': ('remind_3_days_before', 'remind_1_day_before', 'custom_message_before')
        }),
        ('On Due Date', {
            'fields': ('remind_on_due_date', 'custom_message_due')
        }),
        ('After Due Date', {
            'fields': ('remind_3_days_after', 'remind_7_days_after', 'remind_14_days_after', 'custom_message_overdue')
        }),
    )


@admin.register(PaymentReminderLog)
class PaymentReminderLogAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'reminder_type', 'days_offset', 'recipient_email',
        'success', 'sent_at'
    ]
    list_filter = ['reminder_type', 'success', 'sent_at']
    search_fields = ['invoice__invoice_number', 'recipient_email']
    readonly_fields = ['invoice', 'days_offset', 'reminder_type', 'sent_at', 'recipient_email', 'success', 'error_message']
    date_hierarchy = 'sent_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
