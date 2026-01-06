"""
Admin configuration for invoices app.
"""
from django.contrib import admin
from .models import Invoice, LineItem, InvoiceBatch


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
