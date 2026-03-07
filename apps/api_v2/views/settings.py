"""
Settings views for API v2 (payment reminders and late fees).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company
from apps.invoices.models import PaymentReminderSettings
from apps.api_v2.serializers.settings import (
    ReminderSettingsV2Serializer,
    LateFeeSettingsV2Serializer,
)


def _get_or_create_company(user):
    """Return the company for this user, creating a default one if needed."""
    company = user.get_company()
    if company is None:
        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"},
        )
    return company


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def reminder_settings(request):
    """
    GET   /api/v2/settings/reminders/  — retrieve reminder settings
    PUT   /api/v2/settings/reminders/  — full update
    PATCH /api/v2/settings/reminders/  — partial update
    """
    company = _get_or_create_company(request.user)
    settings_obj, _ = PaymentReminderSettings.objects.get_or_create(company=company)

    if request.method == 'GET':
        serializer = ReminderSettingsV2Serializer(settings_obj)
        return Response(serializer.data)

    partial = request.method == 'PATCH'
    serializer = ReminderSettingsV2Serializer(
        settings_obj,
        data=request.data,
        partial=partial,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def late_fee_settings(request):
    """
    GET   /api/v2/settings/late-fees/  — retrieve late fee settings
    PUT   /api/v2/settings/late-fees/  — full update
    PATCH /api/v2/settings/late-fees/  — partial update
    """
    company = _get_or_create_company(request.user)

    if request.method == 'GET':
        serializer = LateFeeSettingsV2Serializer(company)
        return Response(serializer.data)

    partial = request.method == 'PATCH'
    serializer = LateFeeSettingsV2Serializer(
        company,
        data=request.data,
        partial=partial,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
