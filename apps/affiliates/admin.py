from django.contrib import admin
from django.utils import timezone
from .models import Affiliate, Referral, Commission, AffiliateApplication


@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ['user', 'referral_code', 'status', 'total_referrals', 'total_conversions', 'total_earnings', 'pending_earnings', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'referral_code']
    readonly_fields = ['referral_code', 'total_referrals', 'total_conversions', 'total_earnings', 'pending_earnings', 'paid_earnings', 'created_at', 'approved_at']
    actions = ['approve_affiliates', 'suspend_affiliates']

    def approve_affiliates(self, request, queryset):
        for affiliate in queryset.filter(status='pending'):
            affiliate.approve()
        self.message_user(request, f"Approved {queryset.count()} affiliates.")
    approve_affiliates.short_description = "Approve selected affiliates"

    def suspend_affiliates(self, request, queryset):
        queryset.update(status='suspended')
        self.message_user(request, f"Suspended {queryset.count()} affiliates.")
    suspend_affiliates.short_description = "Suspend selected affiliates"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'referred_user', 'converted', 'created_at', 'converted_at']
    list_filter = ['converted', 'created_at']
    search_fields = ['affiliate__user__email', 'affiliate__referral_code', 'referred_user__email']
    readonly_fields = ['visitor_id', 'ip_address', 'user_agent', 'landing_page', 'created_at', 'converted_at']


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'purchase_type', 'purchase_amount', 'amount', 'status', 'created_at']
    list_filter = ['status', 'purchase_type', 'created_at']
    search_fields = ['affiliate__user__email', 'affiliate__referral_code']
    readonly_fields = ['affiliate', 'referral', 'purchase_type', 'purchase_description', 'purchase_amount', 'commission_rate', 'amount', 'stripe_payment_intent_id', 'stripe_invoice_id', 'created_at', 'paid_at']
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        for commission in queryset.filter(status='pending'):
            commission.mark_paid()
        self.message_user(request, f"Marked {queryset.count()} commissions as paid.")
    mark_as_paid.short_description = "Mark selected commissions as paid"


@admin.register(AffiliateApplication)
class AffiliateApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'website', 'reviewed', 'approved', 'created_at']
    list_filter = ['reviewed', 'approved', 'created_at']
    search_fields = ['user__email', 'website']
    readonly_fields = ['user', 'created_at', 'reviewed_at']
    actions = ['approve_applications', 'reject_applications']

    def approve_applications(self, request, queryset):
        for app in queryset.filter(reviewed=False):
            app.approve()
        self.message_user(request, f"Approved {queryset.count()} applications.")
    approve_applications.short_description = "Approve selected applications"

    def reject_applications(self, request, queryset):
        for app in queryset.filter(reviewed=False):
            app.reject("Application rejected by admin.")
        self.message_user(request, f"Rejected {queryset.count()} applications.")
    reject_applications.short_description = "Reject selected applications"
