"""
Client analytics views for API v2.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.invoices.services.client_analytics import ClientPaymentAnalytics


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_stats(request):
    """
    GET /api/v2/clients/stats/?email=<client_email>

    Returns payment rating and statistics for a given client email,
    scoped to invoices belonging to the authenticated user's company.

    Query params:
      email  (required) — the client's email address

    Response:
      {
        "has_history": bool,
        "rating": "A" | "B" | "C" | "D" | "F" | null,
        "description": str,
        "color_class": str,
        "bg_class": str,
        "stats": {
          "total_invoices": int,
          "paid_invoices": int,
          "payment_rate": int | null,
          "average_payment_days": int | null,
          "on_time_rate": int | null,
          "late_payment_count": int,
          "total_paid": str,
          "outstanding_amount": str
        }
      }
    """
    email = request.query_params.get('email', '').strip()

    if not email:
        return Response(
            {'error': 'email query parameter is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Scope analytics to the authenticated user's company
    company = request.user.get_company()
    analytics = ClientPaymentAnalytics(client_email=email, company=company)
    rating_data = analytics.get_payment_rating()
    stats_data = analytics.get_payment_stats()

    # Convert Decimal values to strings for JSON serialisation
    response_stats = {
        **stats_data,
        'total_paid': str(stats_data.get('total_paid', '0.00')),
        'outstanding_amount': str(stats_data.get('outstanding_amount', '0.00')),
    }

    return Response(
        {
            'email': email,
            'has_history': rating_data.get('stats', {}).get('has_history', False) if rating_data.get('stats') else stats_data.get('has_history', False),
            'rating': rating_data.get('rating'),
            'description': rating_data.get('description'),
            'color_class': rating_data.get('color_class'),
            'bg_class': rating_data.get('bg_class'),
            'stats': response_stats,
        }
    )
