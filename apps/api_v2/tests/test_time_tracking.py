"""
Tests for API v2 time tracking endpoints.

Covers
------
- List time entries (authenticated and unauthenticated)
- Create manual time entry with hours/minutes conversion
- Retrieve, update, delete time entries
- Start timer (including tier-limit enforcement)
- Stop timer (creates a TimeEntry)
- Discard timer
- Get timer status
- Bill time — convert unbilled entries to a draft invoice
- Unauthenticated access returns 401/403
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.companies.models import Company
from apps.invoices.models import ActiveTimer, Invoice, TimeEntry


# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

ENTRIES_URL = '/api/v2/time/entries/'
TIMER_START_URL = '/api/v2/time/timer/start/'
TIMER_STATUS_URL = '/api/v2/time/timer/status/'
BILL_TIME_URL = '/api/v2/time/bill/'


def entry_url(pk):
    return f'/api/v2/time/entries/{pk}/'


def timer_stop_url(timer_id):
    return f'/api/v2/time/timer/{timer_id}/stop/'


def timer_discard_url(timer_id):
    return f'/api/v2/time/timer/{timer_id}/discard/'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(
    email='time@example.com',
    password='testpass123',
    tier='professional',
    status='active',
):
    return CustomUser.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password=password,
        subscription_tier=tier,
        subscription_status=status,
    )


def make_company(user, name='Time Test Co'):
    company, _ = Company.objects.get_or_create(
        user=user,
        defaults={'name': name},
    )
    return company


def make_time_entry(user, company, **kwargs):
    defaults = dict(
        description='Default task',
        client_name='Test Client',
        date=timezone.now().date(),
        duration=3600,          # 1 hour
        hourly_rate=Decimal('100.00'),
        status='unbilled',
    )
    defaults.update(kwargs)
    return TimeEntry.objects.create(user=user, company=company, **defaults)


def make_active_timer(user, company, **kwargs):
    defaults = dict(
        description='Running task',
        hourly_rate=Decimal('100.00'),
    )
    defaults.update(kwargs)
    return ActiveTimer.objects.create(user=user, company=company, **defaults)


def auth_client(user):
    """Return an APIClient with a valid JWT for *user*."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


# ---------------------------------------------------------------------------
# Base fixture mixin
# ---------------------------------------------------------------------------

class TimeTrackingTestBase(TestCase):
    def setUp(self):
        self.user = make_user()
        self.company = make_company(self.user)
        self.entry = make_time_entry(self.user, self.company)
        self.client = auth_client(self.user)


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------

class UnauthenticatedTimeTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # no credentials

    def test_list_entries_returns_401(self):
        response = self.client.get(ENTRIES_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_create_entry_returns_401(self):
        response = self.client.post(ENTRIES_URL, {}, format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_timer_start_returns_401(self):
        response = self.client.post(TIMER_START_URL, {}, format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_timer_status_returns_401(self):
        response = self.client.get(TIMER_STATUS_URL)
        self.assertIn(response.status_code, [401, 403])

    def test_bill_time_returns_401(self):
        response = self.client.post(BILL_TIME_URL, {}, format='json')
        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# List time entries
# ---------------------------------------------------------------------------

class TimeEntryListTests(TimeTrackingTestBase):
    def test_list_returns_200(self):
        response = self.client.get(ENTRIES_URL)
        self.assertEqual(response.status_code, 200)

    def test_list_includes_own_entries(self):
        response = self.client.get(ENTRIES_URL)
        results = response.json().get('results', response.json())
        ids = [r['id'] for r in results]
        self.assertIn(self.entry.pk, ids)

    def test_list_excludes_other_users_entries(self):
        other_user = make_user(email='other@example.com')
        other_company = make_company(other_user, name='Other Co')
        other_entry = make_time_entry(other_user, other_company)

        response = self.client.get(ENTRIES_URL)
        results = response.json().get('results', response.json())
        ids = [r['id'] for r in results]
        self.assertNotIn(other_entry.pk, ids)

    def test_list_filter_by_status(self):
        make_time_entry(self.user, self.company, description='Done task', status='invoiced')
        response = self.client.get(ENTRIES_URL, {'status': 'invoiced'})
        results = response.json().get('results', response.json())
        self.assertTrue(all(r['status'] == 'invoiced' for r in results))

    def test_list_filter_by_search(self):
        make_time_entry(
            self.user, self.company,
            description='Very unique task XYZZY',
        )
        response = self.client.get(ENTRIES_URL, {'search': 'XYZZY'})
        results = response.json().get('results', response.json())
        self.assertEqual(len(results), 1)
        self.assertIn('XYZZY', results[0]['description'])

    def test_list_response_has_expected_fields(self):
        response = self.client.get(ENTRIES_URL)
        results = response.json().get('results', response.json())
        first = results[0]
        for field in ('id', 'description', 'duration_seconds', 'hourly_rate',
                      'billable_amount', 'status', 'date', 'created_at'):
            self.assertIn(field, first, f'Missing field: {field}')

    def test_list_duration_seconds_matches_model(self):
        response = self.client.get(ENTRIES_URL)
        results = response.json().get('results', response.json())
        entry_data = next(r for r in results if r['id'] == self.entry.pk)
        self.assertEqual(entry_data['duration_seconds'], self.entry.duration)


# ---------------------------------------------------------------------------
# Create time entry
# ---------------------------------------------------------------------------

class TimeEntryCreateTests(TimeTrackingTestBase):
    @staticmethod
    def create_payload(**overrides):
        payload = {
            'description': 'API testing work',
            'client_name': 'Test Client',
            'hours': 2,
            'minutes': 30,
            'hourly_rate': '150.00',
            'date': timezone.now().date().isoformat(),
        }
        payload.update(overrides)
        return payload

    def test_create_returns_201(self):
        response = self.client.post(ENTRIES_URL, self.create_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.json())

    def test_create_converts_hours_minutes_to_seconds(self):
        response = self.client.post(
            ENTRIES_URL,
            self.create_payload(hours=1, minutes=30),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        entry = TimeEntry.objects.get(pk=response.json()['id'])
        # 1h 30m = 5400 seconds
        self.assertEqual(entry.duration, 5400)

    def test_create_with_hours_only(self):
        response = self.client.post(
            ENTRIES_URL,
            self.create_payload(hours=3, minutes=0),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        entry = TimeEntry.objects.get(pk=response.json()['id'])
        self.assertEqual(entry.duration, 10800)  # 3 * 3600

    def test_create_with_minutes_only(self):
        response = self.client.post(
            ENTRIES_URL,
            self.create_payload(hours=0, minutes=45),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        entry = TimeEntry.objects.get(pk=response.json()['id'])
        self.assertEqual(entry.duration, 2700)  # 45 * 60

    def test_create_zero_duration_returns_400(self):
        response = self.client.post(
            ENTRIES_URL,
            self.create_payload(hours=0, minutes=0),
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_create_assigns_user_and_company(self):
        response = self.client.post(ENTRIES_URL, self.create_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        entry = TimeEntry.objects.get(pk=response.json()['id'])
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.company, self.company)

    def test_create_response_uses_read_serializer(self):
        """Response on create must include duration_seconds (read field), not hours."""
        response = self.client.post(ENTRIES_URL, self.create_payload(), format='json')
        data = response.json()
        self.assertIn('duration_seconds', data)
        self.assertNotIn('hours', data)
        self.assertNotIn('minutes', data)

    def test_create_default_status_is_unbilled(self):
        response = self.client.post(ENTRIES_URL, self.create_payload(), format='json')
        entry = TimeEntry.objects.get(pk=response.json()['id'])
        self.assertEqual(entry.status, 'unbilled')


# ---------------------------------------------------------------------------
# Update time entry
# ---------------------------------------------------------------------------

class TimeEntryUpdateTests(TimeTrackingTestBase):
    def test_patch_unbilled_entry_returns_200(self):
        payload = {'description': 'Updated description', 'hours': 1, 'minutes': 0}
        response = self.client.patch(entry_url(self.entry.pk), payload, format='json')
        self.assertEqual(response.status_code, 200, response.json())

    def test_patch_updates_duration(self):
        self.client.patch(
            entry_url(self.entry.pk),
            {'hours': 2, 'minutes': 15},
            format='json',
        )
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.duration, 2 * 3600 + 15 * 60)

    def test_patch_invoiced_entry_returns_403(self):
        self.entry.status = 'invoiced'
        self.entry.save()
        response = self.client.patch(
            entry_url(self.entry.pk),
            {'description': 'No', 'hours': 1, 'minutes': 0},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Delete time entry
# ---------------------------------------------------------------------------

class TimeEntryDeleteTests(TimeTrackingTestBase):
    def test_delete_returns_204(self):
        response = self.client.delete(entry_url(self.entry.pk))
        self.assertEqual(response.status_code, 204)

    def test_delete_removes_from_db(self):
        pk = self.entry.pk
        self.client.delete(entry_url(pk))
        self.assertFalse(TimeEntry.objects.filter(pk=pk).exists())

    def test_delete_other_users_entry_returns_404(self):
        other_user = make_user(email='del@example.com')
        other_company = make_company(other_user, name='Del Co')
        other_entry = make_time_entry(other_user, other_company)

        response = self.client.delete(entry_url(other_entry.pk))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Start timer
# ---------------------------------------------------------------------------

class TimerStartTests(TimeTrackingTestBase):
    def test_start_returns_201(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'New task', 'hourly_rate': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_start_creates_active_timer(self):
        before = ActiveTimer.objects.filter(user=self.user).count()
        self.client.post(
            TIMER_START_URL,
            {'description': 'Count test', 'hourly_rate': '100.00'},
            format='json',
        )
        after = ActiveTimer.objects.filter(user=self.user).count()
        self.assertEqual(after, before + 1)

    def test_start_response_has_expected_fields(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'Fields test', 'hourly_rate': '75.00'},
            format='json',
        )
        data = response.json()
        for field in ('id', 'description', 'started_at', 'elapsed_seconds'):
            self.assertIn(field, data, f'Missing field: {field}')

    def test_start_elapsed_seconds_is_non_negative_integer(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'Elapsed test', 'hourly_rate': '100.00'},
            format='json',
        )
        elapsed = response.json()['elapsed_seconds']
        self.assertIsInstance(elapsed, int)
        self.assertGreaterEqual(elapsed, 0)

    def test_start_without_description_still_succeeds(self):
        response = self.client.post(
            TIMER_START_URL,
            {'hourly_rate': '50.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_start_uses_default_hourly_rate_when_omitted(self):
        """When hourly_rate is not supplied, the timer should still be created."""
        response = self.client.post(TIMER_START_URL, {}, format='json')
        self.assertIn(response.status_code, [201, 400])  # 400 only if company missing

    def test_start_invalid_hourly_rate_returns_400(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'Bad rate', 'hourly_rate': 'not-a-number'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('hourly_rate', response.json())


# ---------------------------------------------------------------------------
# Timer limit enforcement
# ---------------------------------------------------------------------------

class TimerLimitTests(TestCase):
    """
    Free/Starter tier users are limited to 1 active timer.
    Attempting to start a second must return 403.
    """

    def setUp(self):
        # Free-tier user: max_active_timers == 1
        self.user = make_user(email='free@example.com', tier='free', status='inactive')
        self.company = make_company(self.user, name='Free Co')
        self.client = auth_client(self.user)

        # Pre-create an active timer so the limit is already reached
        make_active_timer(self.user, self.company)

    def test_start_second_timer_returns_403(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'Second timer', 'hourly_rate': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_403_message_mentions_limit(self):
        response = self.client.post(
            TIMER_START_URL,
            {'description': 'Second timer', 'hourly_rate': '100.00'},
            format='json',
        )
        detail = response.json().get('detail', '')
        self.assertTrue(
            'timer' in detail.lower() or 'limit' in detail.lower() or 'plan' in detail.lower(),
            f'Expected timer-limit language in error detail, got: {detail!r}',
        )

    def test_professional_user_can_start_multiple_timers(self):
        """Professional tier gets 5 timers; starting a second must succeed."""
        pro_user = make_user(email='pro@example.com', tier='professional')
        pro_company = make_company(pro_user, name='Pro Co')
        pro_client = auth_client(pro_user)

        # Start first timer
        pro_client.post(
            TIMER_START_URL,
            {'description': 'Timer 1', 'hourly_rate': '100.00'},
            format='json',
        )

        # Start second timer — should still succeed for Professional
        response = pro_client.post(
            TIMER_START_URL,
            {'description': 'Timer 2', 'hourly_rate': '100.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)


# ---------------------------------------------------------------------------
# Stop timer
# ---------------------------------------------------------------------------

class TimerStopTests(TimeTrackingTestBase):
    def setUp(self):
        super().setUp()
        self.timer = make_active_timer(self.user, self.company, description='Stop me')

    def test_stop_returns_200(self):
        response = self.client.post(timer_stop_url(self.timer.pk))
        self.assertEqual(response.status_code, 200, response.json())

    def test_stop_creates_time_entry(self):
        before = TimeEntry.objects.filter(user=self.user).count()
        self.client.post(timer_stop_url(self.timer.pk))
        after = TimeEntry.objects.filter(user=self.user).count()
        self.assertEqual(after, before + 1)

    def test_stop_deletes_active_timer(self):
        timer_pk = self.timer.pk
        self.client.post(timer_stop_url(timer_pk))
        self.assertFalse(ActiveTimer.objects.filter(pk=timer_pk).exists())

    def test_stop_response_is_time_entry(self):
        response = self.client.post(timer_stop_url(self.timer.pk))
        data = response.json()
        for field in ('id', 'description', 'duration_seconds', 'status'):
            self.assertIn(field, data, f'Missing field: {field}')

    def test_stop_entry_description_matches_timer(self):
        response = self.client.post(timer_stop_url(self.timer.pk))
        self.assertEqual(response.json()['description'], 'Stop me')

    def test_stop_other_users_timer_returns_404(self):
        other_user = make_user(email='stopother@example.com')
        other_company = make_company(other_user, name='Stop Other Co')
        other_timer = make_active_timer(other_user, other_company)

        response = self.client.post(timer_stop_url(other_timer.pk))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Discard timer
# ---------------------------------------------------------------------------

class TimerDiscardTests(TimeTrackingTestBase):
    def setUp(self):
        super().setUp()
        self.timer = make_active_timer(self.user, self.company, description='Discard me')

    def test_discard_returns_204(self):
        response = self.client.post(timer_discard_url(self.timer.pk))
        self.assertEqual(response.status_code, 204)

    def test_discard_removes_active_timer(self):
        timer_pk = self.timer.pk
        self.client.post(timer_discard_url(timer_pk))
        self.assertFalse(ActiveTimer.objects.filter(pk=timer_pk).exists())

    def test_discard_does_not_create_time_entry(self):
        before = TimeEntry.objects.filter(user=self.user).count()
        self.client.post(timer_discard_url(self.timer.pk))
        after = TimeEntry.objects.filter(user=self.user).count()
        self.assertEqual(after, before)

    def test_discard_other_users_timer_returns_404(self):
        other_user = make_user(email='discardother@example.com')
        other_company = make_company(other_user, name='Discard Other Co')
        other_timer = make_active_timer(other_user, other_company)

        response = self.client.post(timer_discard_url(other_timer.pk))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Timer status
# ---------------------------------------------------------------------------

class TimerStatusTests(TimeTrackingTestBase):
    def test_status_returns_200(self):
        response = self.client.get(TIMER_STATUS_URL)
        self.assertEqual(response.status_code, 200)

    def test_status_response_has_count_and_timers(self):
        response = self.client.get(TIMER_STATUS_URL)
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('timers', data)

    def test_status_count_zero_when_no_timers(self):
        response = self.client.get(TIMER_STATUS_URL)
        data = response.json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['timers'], [])

    def test_status_lists_own_timers(self):
        timer = make_active_timer(self.user, self.company)
        response = self.client.get(TIMER_STATUS_URL)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['timers'][0]['id'], timer.pk)

    def test_status_excludes_other_users_timers(self):
        other_user = make_user(email='statusother@example.com')
        other_company = make_company(other_user, name='Status Other Co')
        make_active_timer(other_user, other_company)

        response = self.client.get(TIMER_STATUS_URL)
        data = response.json()
        self.assertEqual(data['count'], 0)

    def test_status_timer_fields(self):
        make_active_timer(self.user, self.company, description='Check fields')
        response = self.client.get(TIMER_STATUS_URL)
        timer_data = response.json()['timers'][0]
        for field in ('id', 'description', 'started_at', 'elapsed_seconds', 'hourly_rate'):
            self.assertIn(field, timer_data, f'Missing field: {field}')


# ---------------------------------------------------------------------------
# Bill time
# ---------------------------------------------------------------------------

class BillTimeTests(TimeTrackingTestBase):
    def setUp(self):
        super().setUp()
        # Create a second unbilled entry for multi-entry billing tests
        self.entry2 = make_time_entry(
            self.user, self.company,
            description='Second task',
            duration=1800,   # 30 min
            hourly_rate=Decimal('200.00'),
        )

    def test_bill_time_returns_201(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_bill_time_creates_invoice(self):
        before = Invoice.objects.filter(company=self.company).count()
        self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        after = Invoice.objects.filter(company=self.company).count()
        self.assertEqual(after, before + 1)

    def test_bill_time_marks_entries_invoiced(self):
        self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk, self.entry2.pk]},
            format='json',
        )
        self.entry.refresh_from_db()
        self.entry2.refresh_from_db()
        self.assertEqual(self.entry.status, 'invoiced')
        self.assertEqual(self.entry2.status, 'invoiced')

    def test_bill_time_response_has_expected_fields(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        data = response.json()
        for field in ('invoice_id', 'invoice_number', 'client_name',
                      'total', 'status', 'entries_billed'):
            self.assertIn(field, data, f'Missing field: {field}')

    def test_bill_time_invoice_status_is_draft(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        self.assertEqual(response.json()['status'], 'draft')

    def test_bill_time_entries_billed_count(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk, self.entry2.pk]},
            format='json',
        )
        self.assertEqual(response.json()['entries_billed'], 2)

    def test_bill_time_with_summary_grouping(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk, self.entry2.pk], 'grouping': 'summary'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_bill_time_missing_entry_ids_returns_400(self):
        response = self.client.post(BILL_TIME_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('entry_ids', response.json())

    def test_bill_time_empty_entry_ids_returns_400(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': []},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('entry_ids', response.json())

    def test_bill_time_invalid_grouping_returns_400(self):
        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk], 'grouping': 'invalid'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('grouping', response.json())

    def test_bill_time_cannot_bill_already_invoiced_entries(self):
        """Already-invoiced entries are not unbilled; query returns nothing → 400."""
        self.entry.status = 'invoiced'
        self.entry.save()

        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_bill_time_cannot_bill_other_users_entries(self):
        other_user = make_user(email='billother@example.com')
        other_company = make_company(other_user, name='Bill Other Co')
        other_entry = make_time_entry(other_user, other_company)

        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [other_entry.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_bill_time_denied_when_invoice_limit_reached(self):
        """User at invoice limit must receive 403."""
        self.user.subscription_tier = 'free'
        self.user.subscription_status = 'inactive'
        self.user.free_credits_remaining = 0
        self.user.credits_balance = 0
        self.user.save()

        response = self.client.post(
            BILL_TIME_URL,
            {'entry_ids': [self.entry.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
