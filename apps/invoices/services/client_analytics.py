"""
Client Payment Analytics Service.

Calculates payment statistics for clients based on invoice history.
"""
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from decimal import Decimal


class ClientPaymentAnalytics:
    """Service for analyzing client payment behavior."""

    def __init__(self, client_email, company=None):
        """
        Initialize analytics for a client.

        Args:
            client_email: Email address of the client
            company: Optional Company object to scope invoices
        """
        self.client_email = client_email.lower().strip() if client_email else ''
        self.company = company

    def get_paid_invoices(self):
        """Get all paid invoices for this client."""
        from apps.invoices.models import Invoice

        queryset = Invoice.objects.filter(
            client_email__iexact=self.client_email,
            status='paid'
        )

        if self.company:
            queryset = queryset.filter(company=self.company)

        return queryset

    def get_all_invoices(self):
        """Get all non-draft invoices for this client."""
        from apps.invoices.models import Invoice

        queryset = Invoice.objects.filter(
            client_email__iexact=self.client_email
        ).exclude(status='draft')

        if self.company:
            queryset = queryset.filter(company=self.company)

        return queryset

    def calculate_average_payment_days(self):
        """
        Calculate the average number of days this client takes to pay.

        Returns:
            Average payment days (int) or None if no payment history
        """
        paid_invoices = self.get_paid_invoices().filter(paid_at__isnull=False)

        if not paid_invoices.exists():
            return None

        total_days = 0
        count = 0

        for invoice in paid_invoices:
            payment_days = invoice.get_payment_days()
            if payment_days is not None:
                total_days += payment_days
                count += 1

        if count == 0:
            return None

        return round(total_days / count)

    def get_payment_stats(self):
        """
        Get comprehensive payment statistics for this client.

        Returns:
            dict with payment statistics
        """
        from apps.invoices.models import Invoice

        all_invoices = self.get_all_invoices()
        paid_invoices = self.get_paid_invoices()

        total_count = all_invoices.count()
        paid_count = paid_invoices.count()

        if total_count == 0:
            return {
                'has_history': False,
                'total_invoices': 0,
                'paid_invoices': 0,
                'payment_rate': None,
                'average_payment_days': None,
                'on_time_rate': None,
                'late_payment_count': 0,
                'total_paid': Decimal('0.00'),
                'outstanding_amount': Decimal('0.00'),
            }

        # Calculate average payment days
        average_days = self.calculate_average_payment_days()

        # Count on-time vs late payments
        on_time_count = 0
        late_count = 0

        for invoice in paid_invoices.filter(paid_at__isnull=False):
            payment_days = invoice.get_payment_days()
            if payment_days is not None:
                # Calculate expected days based on payment terms
                terms_days = {
                    'due_on_receipt': 0,
                    'net_15': 15,
                    'net_30': 30,
                    'net_45': 45,
                    'net_60': 60,
                }
                expected_days = terms_days.get(invoice.payment_terms, 30)

                if payment_days <= expected_days:
                    on_time_count += 1
                else:
                    late_count += 1

        # Calculate totals
        total_paid = sum(i.total for i in paid_invoices)

        # Outstanding amount calculation
        outstanding_invoices = all_invoices.exclude(status__in=['paid', 'cancelled'])
        outstanding_amount = sum(i.total for i in outstanding_invoices)

        return {
            'has_history': True,
            'total_invoices': total_count,
            'paid_invoices': paid_count,
            'payment_rate': round((paid_count / total_count) * 100) if total_count > 0 else None,
            'average_payment_days': average_days,
            'on_time_rate': round((on_time_count / (on_time_count + late_count)) * 100) if (on_time_count + late_count) > 0 else None,
            'late_payment_count': late_count,
            'total_paid': total_paid,
            'outstanding_amount': outstanding_amount,
        }

    def get_payment_rating(self):
        """
        Get a simple payment rating for display purposes.

        Returns:
            dict with rating (A-F), description, and color class
        """
        stats = self.get_payment_stats()

        if not stats['has_history']:
            return {
                'rating': None,
                'description': 'New client - no payment history',
                'color_class': 'text-gray-500',
                'bg_class': 'bg-gray-100 dark:bg-gray-700',
            }

        average_days = stats['average_payment_days']
        on_time_rate = stats['on_time_rate']

        if average_days is None and stats['paid_invoices'] == 0:
            return {
                'rating': None,
                'description': f'{stats["total_invoices"]} invoice(s) sent - awaiting payment',
                'color_class': 'text-yellow-600 dark:text-yellow-400',
                'bg_class': 'bg-yellow-50 dark:bg-yellow-900/20',
            }

        # Rating based on average payment days and on-time rate
        if average_days is not None:
            if average_days <= 15 and (on_time_rate is None or on_time_rate >= 90):
                rating = 'A'
                description = f'Excellent payer - pays in {average_days} days on average'
                color_class = 'text-green-600 dark:text-green-400'
                bg_class = 'bg-green-50 dark:bg-green-900/20'
            elif average_days <= 30 and (on_time_rate is None or on_time_rate >= 70):
                rating = 'B'
                description = f'Good payer - pays in {average_days} days on average'
                color_class = 'text-blue-600 dark:text-blue-400'
                bg_class = 'bg-blue-50 dark:bg-blue-900/20'
            elif average_days <= 45 and (on_time_rate is None or on_time_rate >= 50):
                rating = 'C'
                description = f'Average payer - pays in {average_days} days on average'
                color_class = 'text-yellow-600 dark:text-yellow-400'
                bg_class = 'bg-yellow-50 dark:bg-yellow-900/20'
            elif average_days <= 60:
                rating = 'D'
                description = f'Slow payer - pays in {average_days} days on average'
                color_class = 'text-orange-600 dark:text-orange-400'
                bg_class = 'bg-orange-50 dark:bg-orange-900/20'
            else:
                rating = 'F'
                description = f'Poor payer - pays in {average_days} days on average'
                color_class = 'text-red-600 dark:text-red-400'
                bg_class = 'bg-red-50 dark:bg-red-900/20'
        else:
            rating = None
            description = f'{stats["paid_invoices"]} of {stats["total_invoices"]} invoices paid'
            color_class = 'text-gray-600 dark:text-gray-400'
            bg_class = 'bg-gray-50 dark:bg-gray-800'

        return {
            'rating': rating,
            'description': description,
            'color_class': color_class,
            'bg_class': bg_class,
            'stats': stats,
        }


def get_client_payment_summary(client_email, company=None):
    """
    Quick helper function to get a client's payment summary.

    Args:
        client_email: Client email address
        company: Optional Company to scope results

    Returns:
        dict with average_days, rating info, and description
    """
    if not client_email:
        return None

    analytics = ClientPaymentAnalytics(client_email, company)
    rating = analytics.get_payment_rating()

    return {
        'average_days': analytics.calculate_average_payment_days(),
        'rating': rating['rating'],
        'description': rating['description'],
        'color_class': rating['color_class'],
        'bg_class': rating['bg_class'],
    }
