"""
Views for Client Portal.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from io import BytesIO

from .models import Client, ClientSession, ClientPayment
from .services.magic_link import MagicLinkService
from apps.invoices.models import Invoice
from apps.billing.services.stripe_connect import StripeConnectService


class ClientPortalMixin:
    """Mixin for client portal authentication via session cookie."""

    def dispatch(self, request, *args, **kwargs):
        self.client = None
        self.client_session = None

        session_token = request.COOKIES.get('client_session')
        if session_token:
            service = MagicLinkService(request)
            session = service.validate_session(session_token)
            if session:
                self.client = session.client
                self.client_session = session

        if not self.client:
            return redirect('clients:request_access')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['client_session'] = self.client_session
        return context


# ============================================================================
# Authentication Views
# ============================================================================

class RequestAccessView(View):
    """Request access to client portal via magic link."""
    template_name = 'clients/request_access.html'

    def get(self, request):
        # If already logged in, redirect to dashboard
        session_token = request.COOKIES.get('client_session')
        if session_token:
            service = MagicLinkService(request)
            session = service.validate_session(session_token)
            if session:
                return redirect('clients:dashboard')

        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, self.template_name)

        # Check if this email has any invoices
        has_invoices = Invoice.objects.filter(client_email__iexact=email).exists()

        if not has_invoices:
            messages.error(
                request,
                'No invoices found for this email address. '
                'Please check your email or contact the business that sent your invoice.'
            )
            return render(request, self.template_name, {'email': email})

        # Send magic link
        service = MagicLinkService(request)
        result = service.send_magic_link_email(email)

        if result['success']:
            return redirect('clients:check_email')
        else:
            messages.error(request, result.get('error', 'Unable to send access link.'))
            return render(request, self.template_name, {'email': email})


class CheckEmailView(TemplateView):
    """Confirmation page after requesting magic link."""
    template_name = 'clients/check_email.html'


class MagicLinkAuthView(View):
    """Verify magic link token and create session."""

    def get(self, request, token):
        service = MagicLinkService(request)
        result = service.verify_token(token)

        if not result['success']:
            messages.error(request, result.get('error', 'Invalid or expired link.'))
            return redirect('clients:request_access')

        # Create response with redirect
        response = redirect('clients:dashboard')

        # Set session cookie
        response.set_cookie(
            'client_session',
            result['session'].session_token,
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
        )

        messages.success(request, f'Welcome back, {result["client"].get_display_name()}!')

        # If linked to specific invoice, redirect there
        if result.get('invoice'):
            response = redirect('clients:invoice_detail', pk=result['invoice'].id)
            response.set_cookie(
                'client_session',
                result['session'].session_token,
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
            )

        return response


class LogoutView(View):
    """Logout from client portal."""

    def get(self, request):
        session_token = request.COOKIES.get('client_session')

        if session_token:
            service = MagicLinkService(request)
            service.logout(session_token)

        response = redirect('clients:request_access')
        response.delete_cookie('client_session')
        messages.success(request, 'You have been logged out.')
        return response


# ============================================================================
# Portal Views
# ============================================================================

class DashboardView(ClientPortalMixin, TemplateView):
    """Client portal dashboard."""
    template_name = 'clients/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        invoices = self.client.get_invoices()

        # Stats
        context['total_outstanding'] = self.client.get_total_outstanding()
        context['total_paid'] = self.client.get_total_paid()
        context['invoice_count'] = invoices.count()

        # Recent invoices
        context['recent_invoices'] = invoices[:5]

        # Companies
        context['companies'] = self.client.get_companies()

        # Recent payments
        context['recent_payments'] = ClientPayment.objects.filter(
            client=self.client,
            status='succeeded'
        ).order_by('-completed_at')[:5]

        # Overdue invoices
        context['overdue_invoices'] = invoices.filter(
            status='overdue'
        ).order_by('due_date')[:3]

        return context


class InvoiceListView(ClientPortalMixin, ListView):
    """List all invoices for the client."""
    template_name = 'clients/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        queryset = self.client.get_invoices()

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by company
        company_id = self.request.GET.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(invoice_name__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = self.client.get_companies()
        context['status_filter'] = self.request.GET.get('status', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class InvoiceDetailView(ClientPortalMixin, TemplateView):
    """View invoice details with pay option."""
    template_name = 'clients/invoice_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        invoice = get_object_or_404(
            Invoice,
            pk=self.kwargs['pk'],
            client_email__iexact=self.client.email
        )

        context['invoice'] = invoice
        context['company'] = invoice.company

        # Check if company can accept payments
        context['can_pay'] = (
            invoice.status in ['sent', 'overdue'] and
            invoice.company.stripe_connect_account_id and
            invoice.company.stripe_connect_charges_enabled
        )

        # Get any existing payments for this invoice
        context['payments'] = ClientPayment.objects.filter(
            invoice=invoice,
            client=self.client
        ).order_by('-created_at')

        return context


class InitiatePaymentView(ClientPortalMixin, View):
    """Initiate Stripe checkout for invoice payment."""

    def post(self, request, pk):
        invoice = get_object_or_404(
            Invoice,
            pk=pk,
            client_email__iexact=self.client.email
        )

        # Validate invoice can be paid
        if invoice.status not in ['sent', 'overdue']:
            messages.error(request, 'This invoice cannot be paid online.')
            return redirect('clients:invoice_detail', pk=pk)

        # Check company has Stripe Connect
        if not invoice.company.stripe_connect_charges_enabled:
            messages.error(request, 'This business has not set up online payments.')
            return redirect('clients:invoice_detail', pk=pk)

        # Create Stripe checkout session
        service = StripeConnectService()
        success_url = request.build_absolute_uri(
            f'/portal/invoices/{pk}/payment-success/'
        )
        cancel_url = request.build_absolute_uri(
            f'/portal/invoices/{pk}/'
        )

        result = service.create_checkout_session(
            invoice=invoice,
            client=self.client,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not result['success']:
            messages.error(request, result.get('error', 'Unable to initiate payment.'))
            return redirect('clients:invoice_detail', pk=pk)

        # Create pending payment record
        ClientPayment.objects.create(
            client=self.client,
            invoice=invoice,
            stripe_checkout_session_id=result['session_id'],
            amount=invoice.total,
            currency=invoice.currency,
            platform_fee=result.get('platform_fee', 0),
            status='pending',
        )

        return redirect(result['checkout_url'])


class PaymentSuccessView(ClientPortalMixin, TemplateView):
    """Payment success confirmation page."""
    template_name = 'clients/payment_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        invoice = get_object_or_404(
            Invoice,
            pk=self.kwargs['pk'],
            client_email__iexact=self.client.email
        )

        context['invoice'] = invoice

        # Get the payment record
        context['payment'] = ClientPayment.objects.filter(
            invoice=invoice,
            client=self.client
        ).order_by('-created_at').first()

        return context


class PaymentHistoryView(ClientPortalMixin, ListView):
    """List all payments made by the client."""
    template_name = 'clients/payment_history.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        return ClientPayment.objects.filter(
            client=self.client
        ).select_related('invoice', 'invoice__company').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Total paid
        total = ClientPayment.objects.filter(
            client=self.client,
            status='succeeded'
        ).aggregate(total=Sum('amount'))
        context['total_paid'] = total['total'] or 0

        return context


class DownloadStatementView(ClientPortalMixin, View):
    """Download account statement as PDF."""

    def get(self, request):
        from xhtml2pdf import pisa
        from django.template.loader import render_to_string

        # Get date range
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        invoices = self.client.get_invoices()
        payments = ClientPayment.objects.filter(
            client=self.client,
            status='succeeded'
        )

        if start_date:
            invoices = invoices.filter(created_at__date__gte=start_date)
            payments = payments.filter(created_at__date__gte=start_date)

        if end_date:
            invoices = invoices.filter(created_at__date__lte=end_date)
            payments = payments.filter(created_at__date__lte=end_date)

        context = {
            'client': self.client,
            'invoices': invoices,
            'payments': payments,
            'total_outstanding': invoices.filter(
                status__in=['sent', 'overdue']
            ).aggregate(total=Sum('total'))['total'] or 0,
            'total_paid': payments.aggregate(total=Sum('amount'))['total'] or 0,
            'generated_at': timezone.now(),
            'start_date': start_date,
            'end_date': end_date,
        }

        html = render_to_string('clients/statement_pdf.html', context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="statement_{self.client.email}_{timezone.now().date()}.pdf"'
        )

        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)

        return response
