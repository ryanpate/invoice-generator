"""
Time tracking serializers for API v2.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.invoices.models import ActiveTimer, TimeEntry


class TimeEntryV2Serializer(serializers.ModelSerializer):
    """
    Read serializer for TimeEntry.

    Exposes duration as duration_seconds to keep the API surface
    explicit and consistent with ActiveTimerV2Serializer.
    """

    duration_seconds = serializers.IntegerField(source='duration', read_only=True)
    billable_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = TimeEntry
        fields = [
            'id',
            'description',
            'client_name',
            'client_email',
            'duration_seconds',
            'hourly_rate',
            'billable_amount',
            'status',
            'date',
            'invoice',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'billable_amount',
            'invoice',
            'created_at',
            'updated_at',
        ]


class TimeEntryCreateV2Serializer(serializers.ModelSerializer):
    """
    Write serializer for creating and updating time entries.

    Accepts human-friendly ``hours`` (int) and ``minutes`` (int) fields
    and converts them to the model's ``duration`` (seconds) on save.
    Neither field is required individually; the caller may supply either
    or both, and they are summed.  Both default to 0 so that a request
    supplying only ``hours`` still works.

    The ``user`` and ``company`` are taken from the request context and
    must NOT be supplied by the client.
    """

    hours = serializers.IntegerField(
        write_only=True,
        default=0,
        min_value=0,
        help_text='Number of whole hours for this entry.',
    )
    minutes = serializers.IntegerField(
        write_only=True,
        default=0,
        min_value=0,
        max_value=59,
        help_text='Number of additional minutes (0-59) for this entry.',
    )

    class Meta:
        model = TimeEntry
        fields = [
            'description',
            'client_name',
            'client_email',
            'hours',
            'minutes',
            'hourly_rate',
            'billable',
            'date',
            'status',
        ]

    def validate(self, attrs):
        hours = attrs.pop('hours', 0)
        minutes = attrs.pop('minutes', 0)
        duration_seconds = (hours * 3600) + (minutes * 60)
        if duration_seconds <= 0:
            raise serializers.ValidationError(
                'Total duration must be greater than zero. '
                'Provide hours and/or minutes.'
            )
        attrs['duration'] = duration_seconds
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        company = user.get_company()

        if company is None:
            raise serializers.ValidationError(
                'No company found for this user. Create a company profile first.'
            )

        return TimeEntry.objects.create(
            user=user,
            company=company,
            **validated_data,
        )

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ActiveTimerV2Serializer(serializers.ModelSerializer):
    """
    Read serializer for a running ActiveTimer.

    ``elapsed_seconds`` is computed server-side so the client can render
    a live counter without querying started_at independently.
    """

    elapsed_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ActiveTimer
        fields = [
            'id',
            'description',
            'client_name',
            'started_at',
            'elapsed_seconds',
            'hourly_rate',
        ]

    def get_elapsed_seconds(self, obj: ActiveTimer) -> int:
        """Return integer seconds elapsed since the timer was started."""
        delta = timezone.now() - obj.started_at
        return max(0, int(delta.total_seconds()))
