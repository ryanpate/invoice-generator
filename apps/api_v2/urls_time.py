"""
URL configuration for API v2 time tracking endpoints.

Mounted at /api/v2/time/ by apps/api_v2/urls.py.

Routes
------
/api/v2/time/entries/                  TimeEntryV2ViewSet (list, create)
/api/v2/time/entries/{id}/             TimeEntryV2ViewSet (retrieve, update, delete)
/api/v2/time/timer/start/             timer_start
/api/v2/time/timer/{id}/stop/         timer_stop
/api/v2/time/timer/{id}/discard/      timer_discard
/api/v2/time/timer/status/            timer_status
/api/v2/time/bill/                    bill_time
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api_v2.views.time_tracking import (
    TimeEntryV2ViewSet,
    bill_time,
    timer_discard,
    timer_start,
    timer_status,
    timer_stop,
)

router = DefaultRouter()
router.register(r'entries', TimeEntryV2ViewSet, basename='time-entry')

urlpatterns = [
    path('', include(router.urls)),
    path('timer/start/', timer_start, name='timer-start'),
    path('timer/status/', timer_status, name='timer-status'),
    path('timer/<int:timer_id>/stop/', timer_stop, name='timer-stop'),
    path('timer/<int:timer_id>/discard/', timer_discard, name='timer-discard'),
    path('bill/', bill_time, name='bill-time'),
]
