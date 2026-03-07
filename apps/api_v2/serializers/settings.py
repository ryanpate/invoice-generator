"""
Settings serializers for API v2 (payment reminders and late fees).
"""
from rest_framework import serializers

from apps.invoices.models import PaymentReminderSettings
from apps.companies.models import Company


class ReminderSettingsV2Serializer(serializers.ModelSerializer):
    """Serializer for PaymentReminderSettings."""

    class Meta:
        model = PaymentReminderSettings
        fields = [
            'reminders_enabled',
            'remind_3_days_before',
            'remind_1_day_before',
            'remind_on_due_date',
            'remind_3_days_after',
            'remind_7_days_after',
            'remind_14_days_after',
            'cc_business_owner',
            'custom_message_before',
            'custom_message_due',
            'custom_message_overdue',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class LateFeeSettingsV2Serializer(serializers.ModelSerializer):
    """
    Serializer for the late fee fields on Company.

    Exposes only the late-fee subset of Company fields.
    """

    class Meta:
        model = Company
        fields = [
            'late_fees_enabled',
            'late_fee_type',
            'late_fee_amount',
            'late_fee_grace_days',
            'late_fee_max_amount',
        ]
