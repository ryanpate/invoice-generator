"""
Views for invoices app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView, View
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db.models import Q
from django.conf import settings

from .models import Invoice, LineItem, InvoiceBatch, RecurringInvoice, TimeEntry, ActiveTimer, TimeTrackingSettings


class TeamAwareQuerysetMixin:
    """
    Mixin that provides team-aware queryset filtering.

    This allows both company owners and team members to access
    their company's invoices and related objects.
    """

    def get_company(self):
        """Get the user's company (owned or member of)."""
        return self.request.user.get_company()

    def get_team_aware_queryset(self, model_class):
        """
        Get a queryset filtered by the user's company.

        Args:
            model_class: The model class to query (Invoice, RecurringInvoice, InvoiceBatch)

        Returns:
            QuerySet filtered by company, or empty if no company
        """
        company = self.get_company()
        if not company:
            return model_class.objects.none()
        return model_class.objects.filter(company=company)


from .forms import (
    InvoiceForm, LineItemFormSet, BatchUploadForm, SendInvoiceEmailForm,
    RecurringInvoiceForm, RecurringLineItemFormSet, TimeEntryForm,
    TryInvoiceForm,
)
# PDF generator imported lazily to avoid WeasyPrint startup issues
from .services.batch_processor import BatchInvoiceProcessor, get_csv_template
from .services.email_sender import InvoiceEmailService


class LandingPageView(TemplateView):
    """Landing page for non-authenticated users."""
    template_name = 'landing/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        context['templates'] = settings.INVOICE_TEMPLATES
        return context


class PricingPageView(TemplateView):
    """Pricing page."""
    template_name = 'landing/pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class FreelancersLandingPageView(TemplateView):
    """Landing page for freelancers."""
    template_name = 'landing/for-freelancers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class SmallBusinessLandingPageView(TemplateView):
    """Landing page for small businesses."""
    template_name = 'landing/for-small-business.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class ConsultantsLandingPageView(TemplateView):
    """Landing page for consultants."""
    template_name = 'landing/for-consultants.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class CompareLandingPageView(TemplateView):
    """Comparison page vs competitors."""
    template_name = 'landing/compare.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


# Feature Landing Pages
class AIInvoiceGeneratorView(TemplateView):
    """Landing page for AI Invoice Generator feature."""
    template_name = 'features/ai-invoice-generator.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        context['ai_limits'] = settings.AI_GENERATION_LIMITS
        return context


class TimeTrackingView(TemplateView):
    """Landing page for Time Tracking feature."""
    template_name = 'features/time-tracking.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class VoiceInvoiceView(TemplateView):
    """Landing page for Voice-to-Invoice feature."""
    template_name = 'features/voice-invoice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        context['ai_limits'] = settings.AI_GENERATION_LIMITS
        return context


# Template Showcase Views
class TemplateShowcaseView(TemplateView):
    """Base view for template showcase pages."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        context['templates'] = settings.INVOICE_TEMPLATES
        return context


class CleanSlateShowcaseView(TemplateShowcaseView):
    """Showcase page for Clean Slate template."""
    template_name = 'showcase/clean-slate.html'


class ExecutiveShowcaseView(TemplateShowcaseView):
    """Showcase page for Executive template."""
    template_name = 'showcase/executive.html'


class BoldModernShowcaseView(TemplateShowcaseView):
    """Showcase page for Bold Modern template."""
    template_name = 'showcase/bold-modern.html'


class ClassicProfessionalShowcaseView(TemplateShowcaseView):
    """Showcase page for Classic Professional template."""
    template_name = 'showcase/classic-professional.html'


class NeonEdgeShowcaseView(TemplateShowcaseView):
    """Showcase page for Neon Edge template."""
    template_name = 'showcase/neon-edge.html'


# Free Tools Views
class FreeToolView(TemplateView):
    """Base view for free SEO tools."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        return context


class InvoiceCalculatorView(FreeToolView):
    """Invoice calculator tool - calculates invoice totals with line items or hourly rates."""
    template_name = 'tools/invoice-calculator.html'


class LateFeeCalculatorView(FreeToolView):
    """Late fee calculator tool - calculates late payment fees and interest."""
    template_name = 'tools/late-fee-calculator.html'


class ToolsIndexView(FreeToolView):
    """Landing page for all free SEO tools."""
    template_name = 'tools/index.html'


# =============================================================================
# State-Specific Late Fee Data (Programmatic SEO)
# =============================================================================

STATE_LATE_FEE_DATA = {
    'california': {
        'name': 'California',
        'abbreviation': 'CA',
        'max_late_fee': 'No statutory cap; must be "reasonable"',
        'max_interest_rate': '10% per year (constitutional default); commercial transactions often exempt',
        'statutes': ['Cal. Civ. Code \u00a7 1671 (liquidated damages)', 'Cal. Const. Art. XV, \u00a7 1 (usury)'],
        'grace_period': 'No statutory requirement for commercial invoices',
        'key_rules': [
            'Late fees treated as liquidated damages \u2014 presumed valid for commercial contracts.',
            'Courts have upheld 1.5% per month (18% annually) on commercial accounts.',
            'The 10% constitutional usury cap has broad exemptions for B2B transactions.',
            'Late fees that function as penalties with no relation to actual damages are unenforceable.',
        ],
        'notes': 'California uses a "reasonableness" standard. In practice, 1.5%/month (18%/year) is widely used and upheld for commercial accounts.',
        'common_rate': '1.5% per month',
    },
    'texas': {
        'name': 'Texas',
        'abbreviation': 'TX',
        'max_late_fee': 'No statutory cap; 10-12% of amount presumed reasonable',
        'max_interest_rate': '18% per year (usury ceiling, may float to 24-28% for large loans)',
        'statutes': ['Tex. Fin. Code \u00a7 302.001 (maximum interest)', 'Tex. Fin. Code \u00a7 303.009 (usury ceiling)'],
        'grace_period': '1-2 days after due date required',
        'key_rules': [
            'No statutory maximum late fee for commercial invoices \u2014 must be reasonable.',
            'Late fees of 10-12% of outstanding balance are generally presumed reasonable.',
            'Monthly fees that annualize above the usury ceiling violate Texas law.',
            'Late fees must be clearly stated in the contract to be enforceable.',
        ],
        'notes': 'The 18%/year usury ceiling is the key constraint. Any fee effectively exceeding this annual rate could be challenged.',
        'common_rate': '1.5% per month',
    },
    'new-york': {
        'name': 'New York',
        'abbreviation': 'NY',
        'max_late_fee': 'Must be contractually agreed; $50 or 5% of payment (whichever is lower) in some contexts',
        'max_interest_rate': '16% per year (civil usury); 25% criminal usury threshold',
        'statutes': ['N.Y. Gen. Oblig. Law \u00a7 5-501 (usury)', 'N.Y. Banking Law \u00a7 14-a (legal rate)', 'N.Y. Penal Law \u00a7 190.40 (criminal usury)'],
        'grace_period': '5-day grace period commonly referenced',
        'key_rules': [
            'Civil usury cap is 16% per year; criminal usury at 25%.',
            'For loans over $250K, up to 25% is permitted; over $2.5M, no cap.',
            'Default legal rate (no contract) is 9% per year.',
            'Late fees must be agreed in writing before the obligation is incurred.',
        ],
        'notes': 'New York has a structured usury framework. For larger commercial transactions ($250K+), limits are relaxed or eliminated.',
        'common_rate': '1.5% per month',
    },
    'florida': {
        'name': 'Florida',
        'abbreviation': 'FL',
        'max_late_fee': 'No statutory cap; must be reasonable and contractually stated',
        'max_interest_rate': '18% per year simple interest (25% for loans over $500K)',
        'statutes': ['Fla. Stat. \u00a7 687.02 (usurious contracts)', 'Fla. Stat. \u00a7 218.70-80 (Prompt Payment Act)'],
        'grace_period': 'No statutory grace period for commercial invoices',
        'key_rules': [
            'No statutory maximum late fee for commercial invoices.',
            'Interest exceeding 18%/year is usurious for transactions under $500K.',
            'Late fees must be clearly spelled out in contracts.',
            'The Prompt Payment Act (government contracts) specifies 1%/month on late payments.',
        ],
        'notes': 'Florida gives businesses significant flexibility. The 18% annual usury limit for transactions under $500K is the main constraint.',
        'common_rate': '1.5% per month',
    },
    'illinois': {
        'name': 'Illinois',
        'abbreviation': 'IL',
        'max_late_fee': 'No statutory cap; must be reasonable',
        'max_interest_rate': '9% per year (written contracts); 5% (no written contract); commercial exemptions apply',
        'statutes': ['815 ILCS 205/4 (written contract rate)', '815 ILCS 205/1 (default rate)', '815 ILCS 205/4.1a (commercial exemptions)'],
        'grace_period': 'No statutory grace period for commercial invoices',
        'key_rules': [
            'Statutory maximum is 9%/year on written contracts, 5% without.',
            'Most B2B commercial transactions are exempt from these caps.',
            'No specific late fee legislation for commercial invoices.',
            'The Prompt Payment Act (government payments) provides 1%/month after 90 days.',
        ],
        'notes': 'Illinois caps of 9%/5% have broad exemptions for commercial transactions under 815 ILCS 205/4.1a. Most B2B invoices are exempt.',
        'common_rate': '1.5% per month',
    },
    'pennsylvania': {
        'name': 'Pennsylvania',
        'abbreviation': 'PA',
        'max_late_fee': 'No statutory cap; courts have upheld 18% annually',
        'max_interest_rate': '6% per year (default for loans \u226450K); commercial exemptions for larger amounts',
        'statutes': ['41 P.S. \u00a7 201 (maximum lawful rate)', '41 P.S. \u00a7 301 (Loan Interest and Protection Law)'],
        'grace_period': 'No statutory grace period (7 days in construction context)',
        'key_rules': [
            'Default rate is 6%/year for loans of $50K or less.',
            'Business loans over $10K and obligations over $50K are exempt from usury limits.',
            'Courts routinely approve 18%/year on past-due commercial accounts.',
            'Triple damages for usury violations \u2014 a meaningful deterrent.',
        ],
        'notes': 'Pennsylvania has a low default rate (6%) but broad exemptions for commercial transactions. 18%/year is standard and upheld for B2B.',
        'common_rate': '1.5% per month',
    },
    'ohio': {
        'name': 'Ohio',
        'abbreviation': 'OH',
        'max_late_fee': 'No statutory cap; must be in a written contract agreed by both parties',
        'max_interest_rate': '8% per year (default); exempt for principal over $100K',
        'statutes': ['Ohio Rev. Code \u00a7 1343.01 (legal rate)', 'Ohio Rev. Code \u00a7 1343.03 (rate when not stipulated)'],
        'grace_period': 'No statutory grace period',
        'key_rules': [
            'Statutory maximum is 8%/year on written instruments.',
            'Amounts over $100K: parties may agree to any rate.',
            'Interest rates printed on invoices are NOT enforceable (Ohio Supreme Court, 2008).',
            'Both parties must expressly agree to rates in a separate written contract.',
        ],
        'notes': 'Ohio is notable: rates on invoices alone are NOT enforceable. Both parties must agree in a written contract. Include late fee terms in service agreements, not just invoices.',
        'common_rate': '1.5% per month',
    },
    'georgia': {
        'name': 'Georgia',
        'abbreviation': 'GA',
        'max_late_fee': 'No statutory cap; can apply immediately after balance is overdue',
        'max_interest_rate': '1.5% per month (18% annually) on commercial accounts 30+ days past due',
        'statutes': ['O.C.G.A. \u00a7 7-4-2 (legal rate; maximum rate)', 'O.C.G.A. \u00a7 7-4-16 (commercial account interest)'],
        'grace_period': 'No grace period for late fees; 30-day wait before interest charges',
        'key_rules': [
            'Legal default rate is 7%/year when no contract specifies a rate.',
            'Commercial account interest capped at 1.5%/month (18%/year) on amounts 30+ days past due.',
            'No statutory cap on late fees (as distinct from interest).',
            'Late fees can be charged immediately; interest requires 30-day wait.',
        ],
        'notes': 'Georgia distinguishes between late fees (no cap, immediate) and interest (18%/year cap, 30-day wait). This distinction is important for structuring your terms.',
        'common_rate': '1.5% per month',
    },
    'north-carolina': {
        'name': 'North Carolina',
        'abbreviation': 'NC',
        'max_late_fee': '4% of past-due payment amount',
        'max_interest_rate': '8% per year (default); any rate for written contracts over $25K',
        'statutes': ['N.C.G.S. \u00a7 24-1 (legal rate 8%)', 'N.C.G.S. \u00a7 24-10.1 (late fees on credit)', 'N.C.G.S. \u00a7 24-1.1 (rate exemptions)'],
        'grace_period': '15 days past due required before charging late fees',
        'key_rules': [
            'Late fees capped at 4% of the past-due amount.',
            '15-day grace period is a statutory requirement.',
            'Legal rate is 8%; contractual freedom for principal over $25K.',
            'Written contracts with higher rates are enforceable above the $25K threshold.',
        ],
        'notes': 'North Carolina has one of the more structured frameworks: 4% late fee cap and mandatory 15-day grace period. Ensure contracts specify interest rates for amounts over $25K.',
        'common_rate': '4% of payment',
    },
    'new-jersey': {
        'name': 'New Jersey',
        'abbreviation': 'NJ',
        'max_late_fee': 'No statutory cap; courts have upheld 5% late charges on commercial contracts',
        'max_interest_rate': '6% (no contract); 16% (with contract); exempt for loans $50K+',
        'statutes': ['N.J.S.A. \u00a7 31:1-1 (contract rate of interest)', 'N.J.S.A. \u00a7 2C:21-19 (criminal usury)'],
        'grace_period': 'No statutory grace period',
        'key_rules': [
            'Civil rate: 6% without contract, 16% with contract.',
            'Loans of $50K+ are exempt from civil usury limits.',
            'Business entities cannot raise civil usury as a defense.',
            'Criminal usury: 30% for individuals, 50% for business entities.',
            'NJ Supreme Court: liquidated damages in commercial contracts are presumptively reasonable.',
        ],
        'notes': 'New Jersey is very business-friendly. B2B entities cannot claim civil usury, and the criminal threshold for businesses is 50%. Courts presume commercial late fee provisions are reasonable.',
        'common_rate': '1.5% per month',
    },
}


class StateLateFeePage(FreeToolView):
    """State-specific late fee calculator page for programmatic SEO."""
    template_name = 'tools/state-late-fee-calculator.html'

    def get(self, request, *args, **kwargs):
        state_slug = self.kwargs.get('state', '')
        if state_slug not in STATE_LATE_FEE_DATA:
            from django.http import Http404
            raise Http404("State not found")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state_slug = self.kwargs.get('state', '')
        state_data = STATE_LATE_FEE_DATA[state_slug]
        context['state'] = state_data
        context['state_slug'] = state_slug
        context['all_states'] = STATE_LATE_FEE_DATA
        return context


class TryInvoiceView(View):
    """No-signup invoice creator at /try/ — lets visitors build and download a PDF."""

    def get(self, request):
        from datetime import date
        form = TryInvoiceForm(initial={'invoice_date': date.today()})
        return render(request, 'invoices/try.html', {'form': form})

    def post(self, request):
        from datetime import date, timedelta
        from decimal import Decimal
        from .services.pdf_generator import InvoicePDFGenerator

        form = TryInvoiceForm(request.POST)

        # Parse line items from POST data
        line_items = []
        idx = 0
        while True:
            desc = request.POST.get(f'item_description_{idx}')
            if desc is None:
                break
            qty_str = request.POST.get(f'item_quantity_{idx}', '1')
            rate_str = request.POST.get(f'item_rate_{idx}', '0')
            try:
                qty = float(qty_str) if qty_str else 1
                rate = float(rate_str) if rate_str else 0
            except (ValueError, TypeError):
                qty, rate = 1, 0
            if desc.strip():
                line_items.append({
                    'description': desc.strip(),
                    'quantity': qty,
                    'rate': rate,
                    'amount': round(qty * rate, 2),
                })
            idx += 1

        if not form.is_valid() or not line_items:
            if not line_items:
                form.add_error(None, 'Please add at least one line item.')
            return render(request, 'invoices/try.html', {'form': form})

        cd = form.cleaned_data
        tax_rate = float(cd.get('tax_rate') or 0)
        subtotal = sum(item['amount'] for item in line_items)
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal + tax_amount, 2)

        # Calculate due date from payment terms
        invoice_date = cd['invoice_date']
        terms_days = {'due_on_receipt': 0, 'net_15': 15, 'net_30': 30, 'net_45': 45, 'net_60': 60, 'net_90': 90}
        due_date = invoice_date + timedelta(days=terms_days.get(cd['payment_terms'], 30))

        invoice_data = {
            'invoice_number': 'INV-PREVIEW',
            'client_name': cd['client_name'],
            'client_email': cd.get('client_email', ''),
            'client_phone': '',
            'client_address': '',
            'invoice_date': invoice_date,
            'due_date': due_date,
            'payment_terms': cd['payment_terms'],
            'currency': cd['currency'],
            'subtotal': Decimal(str(subtotal)),
            'tax_rate': Decimal(str(tax_rate)),
            'tax_amount': Decimal(str(tax_amount)),
            'total': Decimal(str(total)),
            'notes': cd.get('notes', ''),
            'template_style': cd['template_style'],
            'line_items': line_items,
        }

        # Build a mock company object for the PDF generator
        class TryCompany:
            name = cd['company_name']
            email = cd.get('company_email', '')
            phone = ''
            website = ''
            address_line1 = ''
            address_line2 = ''
            city = ''
            state = ''
            postal_code = ''
            country = ''
            tax_id = ''
            accent_color = ''
            logo = None
            signature = None
            class user:
                @staticmethod
                def shows_watermark():
                    return True  # Always watermark on /try/

        pdf_bytes = InvoicePDFGenerator.generate_preview(invoice_data, TryCompany())

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="invoice-preview.pdf"'
        return response


class InvoiceListView(LoginRequiredMixin, TeamAwareQuerysetMixin, ListView):
    """List all invoices for the current user's company (including team members)."""
    model = Invoice
    template_name = 'invoices/list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        queryset = self.get_team_aware_queryset(Invoice).select_related('company')

        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(client_name__icontains=search) |
                Q(client_email__icontains=search)
            )

        # Status filter
        status = self.request.GET.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Invoice.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class InvoiceDetailView(LoginRequiredMixin, TeamAwareQuerysetMixin, DetailView):
    """View single invoice details."""
    model = Invoice
    template_name = 'invoices/detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        return self.get_team_aware_queryset(Invoice).prefetch_related('line_items')


class InvoiceCreateView(LoginRequiredMixin, TeamAwareQuerysetMixin, CreateView):
    """Create a new invoice."""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoices/create.html'

    def dispatch(self, request, *args, **kwargs):
        # Let LoginRequiredMixin handle authentication first
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Check if user can create more invoices
        if not request.user.can_create_invoice():
            messages.error(
                request,
                'You have reached your invoice limit for this month. '
                'Please upgrade your plan to create more invoices.'
            )
            return redirect('billing:plans')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['company'] = self.get_company()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['line_items'] = LineItemFormSet(self.request.POST)
        else:
            context['line_items'] = LineItemFormSet()
        context['templates'] = settings.INVOICE_TEMPLATES
        context['available_templates'] = self.request.user.get_available_templates()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        line_items = context['line_items']

        # Get company (team-aware: owned or member of)
        company = self.get_company()
        if not company:
            # Create company for owner if none exists
            from apps.companies.models import Company
            company = Company.objects.create(
                user=self.request.user,
                owner=self.request.user,
                name=f"{self.request.user.username}'s Company"
            )

        form.instance.company = company
        form.instance.invoice_number = company.get_next_invoice_number()

        if line_items.is_valid():
            self.object = form.save()
            line_items.instance = self.object
            line_items.save()

            # Recalculate totals
            self.object.due_date = self.object.calculate_due_date()
            self.object.calculate_totals()
            self.object.save()

            # Increment user's invoice count
            self.request.user.increment_invoice_count()

            messages.success(self.request, f'Invoice {self.object.invoice_number} created successfully!')
            return redirect('invoices:detail', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class InvoiceUpdateView(LoginRequiredMixin, TeamAwareQuerysetMixin, UpdateView):
    """Edit an existing invoice."""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoices/edit.html'

    def get_queryset(self):
        return self.get_team_aware_queryset(Invoice)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['company'] = self.object.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['line_items'] = LineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['line_items'] = LineItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        line_items = context['line_items']

        if line_items.is_valid():
            self.object = form.save()
            line_items.save()

            # Recalculate totals
            self.object.calculate_totals()
            self.object.save()

            messages.success(self.request, 'Invoice updated successfully!')
            return redirect('invoices:detail', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class InvoiceDeleteView(LoginRequiredMixin, TeamAwareQuerysetMixin, DeleteView):
    """Delete an invoice."""
    model = Invoice
    template_name = 'invoices/delete_confirm.html'
    success_url = reverse_lazy('invoices:list')

    def get_queryset(self):
        return self.get_team_aware_queryset(Invoice)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Invoice deleted successfully.')
        return super().delete(request, *args, **kwargs)


def get_team_aware_object(model_class, pk, user):
    """
    Get an object by pk, filtered by the user's company.

    Helper function for function-based views to enforce team-aware access.
    """
    company = user.get_company()
    if not company:
        return None
    return model_class.objects.filter(company=company, pk=pk).first()


@login_required
def generate_pdf(request, pk):
    """Generate PDF for an invoice."""
    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        messages.error(request, 'Invoice not found.')
        return redirect('invoices:list')

    # Lazy import to avoid WeasyPrint startup issues
    from .services.pdf_generator import InvoicePDFGenerator

    try:
        generator = InvoicePDFGenerator(invoice)
        pdf_bytes = generator.generate()
    except RuntimeError as e:
        messages.error(request, str(e))
        return redirect('invoices:detail', pk=pk)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response


@login_required
def download_pdf(request, pk):
    """Download saved PDF for an invoice."""
    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        messages.error(request, 'Invoice not found.')
        return redirect('invoices:list')

    if not invoice.pdf_file:
        # Lazy import to avoid WeasyPrint startup issues
        from .services.pdf_generator import InvoicePDFGenerator

        try:
            generator = InvoicePDFGenerator(invoice)
            generator.save_to_invoice()
        except RuntimeError as e:
            messages.error(request, str(e))
            return redirect('invoices:detail', pk=pk)

    return FileResponse(
        invoice.pdf_file.open('rb'),
        as_attachment=True,
        filename=f"{invoice.invoice_number}.pdf"
    )


class BatchUploadView(LoginRequiredMixin, TeamAwareQuerysetMixin, TemplateView):
    """Batch invoice upload page."""
    template_name = 'invoices/batch_upload.html'

    def dispatch(self, request, *args, **kwargs):
        # Let LoginRequiredMixin handle authentication first
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Check if user has batch upload feature
        if not request.user.has_batch_upload():
            messages.error(
                request,
                'Batch upload requires a Professional plan or higher. '
                'Please upgrade to access this feature.'
            )
            return redirect('billing:plans')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BatchUploadForm()
        context['recent_batches'] = self.get_team_aware_queryset(
            InvoiceBatch
        ).order_by('-created_at')[:5]
        return context

    def post(self, request, *args, **kwargs):
        form = BatchUploadForm(request.POST, request.FILES)

        if form.is_valid():
            # Get company (team-aware: owned or member of)
            company = self.get_company()
            if not company:
                # Create company for owner if none exists
                from apps.companies.models import Company
                company = Company.objects.create(
                    user=request.user,
                    owner=request.user,
                    name=f"{request.user.username}'s Company"
                )

            # Create batch record
            batch = InvoiceBatch.objects.create(
                company=company,
                csv_file=form.cleaned_data['csv_file']
            )

            # Process batch
            processor = BatchInvoiceProcessor(batch)
            result = processor.process()

            if result['success']:
                messages.success(
                    request,
                    f"Successfully processed {result['processed']} of {result['total']} invoices."
                )
                return redirect('invoices:batch_result', pk=batch.pk)
            else:
                messages.error(request, f"Batch processing failed: {result['error']}")

        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class BatchResultView(LoginRequiredMixin, TeamAwareQuerysetMixin, DetailView):
    """View batch processing results."""
    model = InvoiceBatch
    template_name = 'invoices/batch_result.html'
    context_object_name = 'batch'

    def get_queryset(self):
        return self.get_team_aware_queryset(InvoiceBatch)


@login_required
def download_csv_template(request):
    """Download CSV template for batch upload."""
    csv_content = get_csv_template()
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoice_batch_template.csv"'
    return response


@login_required
def download_batch_zip(request, pk):
    """Download ZIP file from batch processing."""
    batch = get_team_aware_object(InvoiceBatch, pk, request.user)
    if not batch:
        messages.error(request, 'Batch not found.')
        return redirect('invoices:batch')

    if not batch.zip_file:
        messages.error(request, 'No ZIP file available for this batch.')
        return redirect('invoices:batch_result', pk=pk)

    return FileResponse(
        batch.zip_file.open('rb'),
        as_attachment=True,
        filename=f"invoices_batch_{batch.pk}.zip"
    )


@login_required
def mark_invoice_status(request, pk, status):
    """Update invoice status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)

    valid_statuses = [s[0] for s in Invoice.STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    invoice.status = status
    invoice.save(update_fields=['status', 'updated_at'])

    messages.success(request, f'Invoice marked as {status}.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'status': status})

    return redirect('invoices:detail', pk=pk)


@login_required
def toggle_invoice_reminders(request, pk):
    """Toggle payment reminders for a specific invoice."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)

    # Toggle the reminders_paused field
    invoice.reminders_paused = not invoice.reminders_paused
    invoice.save(update_fields=['reminders_paused', 'updated_at'])

    if invoice.reminders_paused:
        messages.success(request, 'Payment reminders paused for this invoice.')
    else:
        messages.success(request, 'Payment reminders resumed for this invoice.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'reminders_paused': invoice.reminders_paused
        })

    return redirect('invoices:detail', pk=pk)


@login_required
def toggle_invoice_late_fees(request, pk):
    """Toggle late fees for a specific invoice."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)

    # Toggle the late_fees_paused field
    invoice.late_fees_paused = not invoice.late_fees_paused
    invoice.save(update_fields=['late_fees_paused', 'updated_at'])

    if invoice.late_fees_paused:
        messages.success(request, 'Late fees paused for this invoice.')
    else:
        messages.success(request, 'Late fees resumed for this invoice.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'late_fees_paused': invoice.late_fees_paused
        })

    return redirect('invoices:detail', pk=pk)


class InvoiceSendEmailView(LoginRequiredMixin, TeamAwareQuerysetMixin, FormView):
    """View for sending invoice via email."""
    template_name = 'invoices/send_email.html'
    form_class = SendInvoiceEmailForm

    def dispatch(self, request, *args, **kwargs):
        # Let LoginRequiredMixin handle authentication first
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # Get invoice after confirming user is authenticated (team-aware)
        self.invoice = get_team_aware_object(Invoice, self.kwargs['pk'], request.user)
        if not self.invoice:
            messages.error(request, 'Invoice not found.')
            return redirect('invoices:list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Pre-populate form with defaults."""
        email_service = InvoiceEmailService(self.invoice)
        return {
            'to_email': self.invoice.client_email or '',
            'subject': email_service.get_default_subject(),
            'message': email_service.get_default_message(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.invoice
        return context

    def form_valid(self, form):
        email_service = InvoiceEmailService(self.invoice)
        result = email_service.send(
            to_email=form.cleaned_data['to_email'],
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message'],
            cc_emails=form.cleaned_data.get('cc_emails', []),
        )

        if result['success']:
            messages.success(
                self.request,
                f'Invoice {self.invoice.invoice_number} sent successfully to {form.cleaned_data["to_email"]}!'
            )
            return redirect('invoices:detail', pk=self.invoice.pk)
        else:
            messages.error(
                self.request,
                f'Failed to send email: {result.get("error", "Unknown error")}'
            )
            return self.form_invalid(form)


# =============================================================================
# Recurring Invoice Views
# =============================================================================

class RecurringInvoiceListView(LoginRequiredMixin, TeamAwareQuerysetMixin, ListView):
    """List all recurring invoices for the current user's company."""
    model = RecurringInvoice
    template_name = 'invoices/recurring/list.html'
    context_object_name = 'recurring_invoices'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if not request.user.has_recurring_invoices():
            messages.error(
                request,
                'Recurring invoices require a Professional plan or higher. '
                'Please upgrade to access this feature.'
            )
            return redirect('billing:plans')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.get_team_aware_queryset(
            RecurringInvoice
        ).select_related('company', 'last_invoice')

        # Status filter
        status = self.request.GET.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)

        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(client_name__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = RecurringInvoice.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')
        context['search_query'] = self.request.GET.get('search', '')
        context['can_create'] = self.request.user.can_create_recurring_invoice()
        context['max_recurring'] = self.request.user.get_recurring_invoice_limit()
        return context


class RecurringInvoiceDetailView(LoginRequiredMixin, TeamAwareQuerysetMixin, DetailView):
    """View recurring invoice details."""
    model = RecurringInvoice
    template_name = 'invoices/recurring/detail.html'
    context_object_name = 'recurring'

    def get_queryset(self):
        return self.get_team_aware_queryset(
            RecurringInvoice
        ).select_related('company', 'last_invoice').prefetch_related('line_items')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get generated invoices
        context['generated_invoices'] = Invoice.objects.filter(
            invoice_name=self.object.name,
            company=self.object.company
        ).order_by('-created_at')[:10]
        return context


class RecurringInvoiceCreateView(LoginRequiredMixin, TeamAwareQuerysetMixin, CreateView):
    """Create a new recurring invoice."""
    model = RecurringInvoice
    form_class = RecurringInvoiceForm
    template_name = 'invoices/recurring/create.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if not request.user.has_recurring_invoices():
            messages.error(
                request,
                'Recurring invoices require a Professional plan or higher.'
            )
            return redirect('billing:plans')

        if not request.user.can_create_recurring_invoice():
            messages.error(
                request,
                'You have reached your limit for recurring invoices. '
                'Please upgrade your plan or cancel an existing recurring invoice.'
            )
            return redirect('invoices:recurring_list')

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['company'] = self.get_company()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['line_items'] = RecurringLineItemFormSet(self.request.POST)
        else:
            context['line_items'] = RecurringLineItemFormSet()
        context['templates'] = settings.INVOICE_TEMPLATES
        context['available_templates'] = self.request.user.get_available_templates()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        line_items = context['line_items']

        # Get company (team-aware: owned or member of)
        company = self.get_company()
        if not company:
            # Create company for owner if none exists
            from apps.companies.models import Company
            company = Company.objects.create(
                user=self.request.user,
                owner=self.request.user,
                name=f"{self.request.user.username}'s Company"
            )

        form.instance.company = company
        form.instance.next_run_date = form.cleaned_data['start_date']

        if line_items.is_valid():
            self.object = form.save()
            line_items.instance = self.object
            line_items.save()

            messages.success(
                self.request,
                f'Recurring invoice "{self.object.name}" created successfully!'
            )
            return redirect('invoices:recurring_detail', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RecurringInvoiceUpdateView(LoginRequiredMixin, TeamAwareQuerysetMixin, UpdateView):
    """Edit an existing recurring invoice."""
    model = RecurringInvoice
    form_class = RecurringInvoiceForm
    template_name = 'invoices/recurring/edit.html'

    def get_queryset(self):
        return self.get_team_aware_queryset(RecurringInvoice)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['company'] = self.object.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['line_items'] = RecurringLineItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['line_items'] = RecurringLineItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        line_items = context['line_items']

        if line_items.is_valid():
            self.object = form.save()
            line_items.save()

            messages.success(self.request, 'Recurring invoice updated successfully!')
            return redirect('invoices:recurring_detail', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RecurringInvoiceDeleteView(LoginRequiredMixin, TeamAwareQuerysetMixin, DeleteView):
    """Delete a recurring invoice."""
    model = RecurringInvoice
    template_name = 'invoices/recurring/delete_confirm.html'
    success_url = reverse_lazy('invoices:recurring_list')

    def get_queryset(self):
        return self.get_team_aware_queryset(RecurringInvoice)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Recurring invoice deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def recurring_toggle_status(request, pk):
    """Toggle recurring invoice status between active and paused."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    recurring = get_team_aware_object(RecurringInvoice, pk, request.user)
    if not recurring:
        return JsonResponse({'error': 'Recurring invoice not found'}, status=404)

    if recurring.status == 'active':
        recurring.pause()
        new_status = 'paused'
        message = f'Recurring invoice "{recurring.name}" paused.'
    elif recurring.status == 'paused':
        recurring.resume()
        new_status = 'active'
        message = f'Recurring invoice "{recurring.name}" resumed.'
    else:
        return JsonResponse({'error': 'Cannot toggle cancelled invoice'}, status=400)

    messages.success(request, message)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'status': new_status})

    return redirect('invoices:recurring_detail', pk=pk)


@login_required
def recurring_generate_now(request, pk):
    """Manually generate an invoice from a recurring invoice."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    recurring = get_team_aware_object(RecurringInvoice, pk, request.user)
    if not recurring:
        messages.error(request, 'Recurring invoice not found.')
        return redirect('invoices:recurring_list')

    if not request.user.has_recurring_invoices():
        messages.error(request, 'You no longer have access to recurring invoices.')
        return redirect('billing:plans')

    if not request.user.can_create_invoice():
        messages.error(
            request,
            'You have reached your invoice limit for this month. '
            'Please upgrade your plan to create more invoices.'
        )
        return redirect('billing:plans')

    try:
        invoice = recurring.generate_invoice()
        request.user.increment_invoice_count()

        messages.success(
            request,
            f'Invoice {invoice.invoice_number} generated from "{recurring.name}"!'
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'invoice_id': invoice.pk,
                'invoice_number': invoice.invoice_number
            })

        return redirect('invoices:detail', pk=invoice.pk)

    except Exception as e:
        messages.error(request, f'Failed to generate invoice: {str(e)}')
        return redirect('invoices:recurring_detail', pk=pk)


@login_required
def convert_to_recurring(request, pk):
    """
    Convert an existing invoice to a recurring invoice template.
    One-click creation of recurring invoice from existing invoice data.
    """
    from django.utils import timezone

    # Get the invoice (team-aware)
    invoice = get_team_aware_object(Invoice, pk, request.user)
    if not invoice:
        messages.error(request, 'Invoice not found.')
        return redirect('invoices:list')

    # Check recurring invoice access
    if not request.user.has_recurring_invoices():
        messages.error(
            request,
            'Recurring invoices require a Professional plan or higher. '
            'Upgrade to create recurring invoices.'
        )
        return redirect('billing:plans')

    # Check recurring invoice limit
    if not request.user.can_create_recurring_invoice():
        messages.error(
            request,
            'You have reached your limit for recurring invoices. '
            'Please upgrade your plan or cancel an existing recurring invoice.'
        )
        return redirect('invoices:recurring_list')

    if request.method == 'POST':
        # Get frequency from form (default to monthly)
        frequency = request.POST.get('frequency', 'monthly')
        start_date_str = request.POST.get('start_date')

        # Parse start date or default to today
        if start_date_str:
            try:
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = timezone.now().date()
        else:
            start_date = timezone.now().date()

        # Create recurring invoice from this invoice
        recurring = RecurringInvoice.objects.create(
            company=invoice.company,
            name=invoice.invoice_name or f"Recurring - {invoice.client_name}",
            client_name=invoice.client_name,
            client_email=invoice.client_email,
            client_phone=invoice.client_phone,
            client_address=invoice.client_address,
            frequency=frequency,
            start_date=start_date,
            next_run_date=start_date,
            currency=invoice.currency,
            payment_terms=invoice.payment_terms,
            tax_rate=invoice.tax_rate,
            template_style=invoice.template_style,
            notes=invoice.notes,
            status='active',
            send_email_on_generation=True,
            auto_send_to_client=bool(invoice.client_email),
        )

        # Copy line items from invoice to recurring invoice
        from .models import RecurringLineItem
        for item in invoice.line_items.all():
            RecurringLineItem.objects.create(
                recurring_invoice=recurring,
                description=item.description,
                quantity=item.quantity,
                rate=item.rate,
                order=item.order,
            )

        messages.success(
            request,
            f'Recurring invoice "{recurring.name}" created successfully! '
            f'It will generate invoices {recurring.get_frequency_display().lower()}.'
        )

        return redirect('invoices:recurring_detail', pk=recurring.pk)

    # GET request - show confirmation modal/form
    # For simplicity, we'll just render a simple confirmation page
    context = {
        'invoice': invoice,
        'frequencies': RecurringInvoice.FREQUENCY_CHOICES,
        'default_start_date': timezone.now().date().isoformat(),
    }
    return render(request, 'invoices/convert_to_recurring.html', context)


# =============================================================================
# Public Invoice Views (for QR code links - no auth required)
# =============================================================================

class PublicInvoiceView(DetailView):
    """Public invoice view accessible via QR code link."""
    model = Invoice
    template_name = 'invoices/public_view.html'
    context_object_name = 'invoice'
    slug_field = 'public_token'
    slug_url_kwarg = 'token'

    def get_queryset(self):
        return Invoice.objects.select_related('company').prefetch_related('line_items')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.object.company
        context['line_items'] = self.object.line_items.all()
        return context


class PublicInvoiceMarkPaidView(View):
    """Allow clients to mark invoice as paid from public view."""

    def post(self, request, token):
        invoice = get_object_or_404(Invoice, public_token=token)

        # Only allow marking as paid if not already paid or cancelled
        if invoice.status in ['paid', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': 'Invoice is already paid or cancelled'
            }, status=400)

        invoice.mark_as_paid()

        # Check if request is AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Invoice marked as paid'
            })

        # For non-AJAX, redirect back to public view
        return redirect('invoices:public_invoice', token=token)


def public_invoice_pdf(request, token):
    """Download PDF from public invoice view."""
    invoice = get_object_or_404(Invoice, public_token=token)

    from .services.pdf_generator import InvoicePDFGenerator

    try:
        generator = InvoicePDFGenerator(invoice)
        pdf_bytes = generator.generate()
    except RuntimeError as e:
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response


@login_required
def ai_generate_line_items(request):
    """
    AJAX endpoint to generate invoice line items using AI.

    Accepts a POST request with a work description and returns
    structured line items generated by Claude.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    # Check if AJAX request
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'AJAX required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
    except json.JSONDecodeError:
        description = request.POST.get('description', '')

    if not description:
        return JsonResponse({
            'success': False,
            'error': 'Please provide a work description.'
        })

    # Use the AI generator service
    from .services.ai_generator import AIInvoiceGenerator

    generator = AIInvoiceGenerator(request.user)
    result = generator.generate_line_items(description)

    if result['success']:
        # Include remaining generations in response
        remaining = request.user.get_ai_generations_remaining()
        result['remaining'] = remaining
        result['is_unlimited'] = remaining is None

    return JsonResponse(result)


def ai_voice_generate(request):
    """
    AJAX endpoint to generate full invoice data from voice audio.

    Accepts a POST with base64 audio data. Works for both authenticated
    users (quota-based) and guests (session-based cap of 1).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'AJAX required'}, status=400)

    import json as json_mod
    try:
        data = json_mod.loads(request.body)
    except json_mod.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

    audio_data = data.get('audio_data', '')
    media_type = data.get('media_type', '')

    if not audio_data:
        return JsonResponse({'success': False, 'error': 'No audio data provided.'})

    if not media_type:
        return JsonResponse({'success': False, 'error': 'No media type provided.'})

    # Quota check: authenticated user or guest session
    if request.user.is_authenticated:
        if not request.user.can_use_ai_generator():
            remaining = request.user.get_ai_generations_remaining()
            limit = request.user.get_ai_generation_limit()
            return JsonResponse({
                'success': False,
                'error': f"You've used all {limit} AI generations this month. Upgrade your plan for more."
            })
    else:
        used = request.session.get('voice_generations_used', 0)
        if used >= 1:
            return JsonResponse({
                'success': False,
                'error': 'Sign up free to keep using voice invoicing.'
            })

    # Generate invoice data from audio
    from .services.ai_generator import AIInvoiceGenerator

    user = request.user if request.user.is_authenticated else None
    generator = AIInvoiceGenerator(user)
    result = generator.generate_from_audio(audio_data, media_type)

    if result['success']:
        # Increment usage
        if request.user.is_authenticated:
            request.user.increment_ai_generation()
            remaining = request.user.get_ai_generations_remaining()
            result['remaining'] = remaining
            result['is_unlimited'] = remaining is None
        else:
            request.session['voice_generations_used'] = request.session.get('voice_generations_used', 0) + 1
            result['remaining'] = 0
            result['is_unlimited'] = False

    return JsonResponse(result)


@login_required
def client_payment_stats(request):
    """
    AJAX endpoint to get payment statistics for a client by email.

    Returns JSON with payment history, average days, and rating.
    """
    client_email = request.GET.get('email', '').strip()

    if not client_email:
        return JsonResponse({
            'success': False,
            'error': 'Email parameter required'
        }, status=400)

    # Get user's company
    company = request.user.get_company()

    from .services.client_analytics import get_client_payment_summary

    summary = get_client_payment_summary(client_email, company)

    if summary is None:
        return JsonResponse({
            'success': True,
            'has_history': False,
            'message': 'No payment history for this client'
        })

    return JsonResponse({
        'success': True,
        'has_history': summary.get('rating') is not None or summary.get('average_days') is not None,
        'average_days': summary.get('average_days'),
        'rating': summary.get('rating'),
        'description': summary.get('description'),
        'color_class': summary.get('color_class'),
        'bg_class': summary.get('bg_class'),
    })


# =============================================================================
# Time Tracking Views
# =============================================================================

class TimeEntryListView(LoginRequiredMixin, TeamAwareQuerysetMixin, ListView):
    """List all time entries for the current user's company."""
    model = TimeEntry
    template_name = 'time_tracking/list.html'
    context_object_name = 'entries'
    paginate_by = 25

    def get_queryset(self):
        queryset = self.get_team_aware_queryset(TimeEntry).select_related('user', 'invoice')

        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(client_name__icontains=search) |
                Q(client_email__icontains=search)
            )

        # Status filter
        status = self.request.GET.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)

        # Date filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Billable filter
        billable = self.request.GET.get('billable')
        if billable == 'yes':
            queryset = queryset.filter(billable=True)
        elif billable == 'no':
            queryset = queryset.filter(billable=False)

        return queryset.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = TimeEntry.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')

        # Get active timers for this user
        context['active_timers'] = self.request.user.active_timers.all()

        # Get unbilled totals
        company = self.get_company()
        if company:
            unbilled = TimeEntry.objects.filter(
                company=company,
                status='unbilled',
                billable=True
            )
            from django.db.models import Sum
            from decimal import Decimal
            total_seconds = unbilled.aggregate(total=Sum('duration'))['total'] or 0
            context['unbilled_hours'] = Decimal(str(total_seconds)) / Decimal('3600')
            # Calculate approximate value
            total_value = sum(e.billable_amount for e in unbilled)
            context['unbilled_value'] = total_value

        return context


class TimeEntryCreateView(LoginRequiredMixin, TeamAwareQuerysetMixin, CreateView):
    """Create a new time entry."""
    model = TimeEntry
    form_class = TimeEntryForm
    template_name = 'time_tracking/create.html'
    success_url = reverse_lazy('invoices:time_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs

    def form_valid(self, form):
        company = self.get_company()
        if not company:
            messages.error(self.request, 'You need to create a company first.')
            return redirect('companies:create')

        form.instance.company = company
        form.instance.user = self.request.user
        messages.success(self.request, 'Time entry created successfully.')
        return super().form_valid(form)


class TimeEntryUpdateView(LoginRequiredMixin, TeamAwareQuerysetMixin, UpdateView):
    """Edit a time entry (only unbilled entries)."""
    model = TimeEntry
    form_class = TimeEntryForm
    template_name = 'time_tracking/edit.html'
    success_url = reverse_lazy('invoices:time_list')

    def get_queryset(self):
        return self.get_team_aware_queryset(TimeEntry).filter(status='unbilled')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Time entry updated successfully.')
        return super().form_valid(form)


class TimeEntryDeleteView(LoginRequiredMixin, TeamAwareQuerysetMixin, DeleteView):
    """Delete a time entry (only unbilled entries)."""
    model = TimeEntry
    template_name = 'time_tracking/delete_confirm.html'
    success_url = reverse_lazy('invoices:time_list')

    def get_queryset(self):
        return self.get_team_aware_queryset(TimeEntry).filter(status='unbilled')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Time entry deleted.')
        return super().delete(request, *args, **kwargs)


class BillTimeView(LoginRequiredMixin, TeamAwareQuerysetMixin, TemplateView):
    """View to select and bill time entries."""
    template_name = 'time_tracking/bill_time.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()

        if not company:
            context['entries'] = []
            return context

        # Get all unbilled, billable entries
        entries = TimeEntry.objects.filter(
            company=company,
            status='unbilled',
            billable=True
        ).select_related('user').order_by('client_email', '-date')

        context['entries'] = entries

        # Group entries by client for display
        from collections import defaultdict
        grouped = defaultdict(list)
        for entry in entries:
            key = entry.client_email or 'No Client'
            grouped[key].append(entry)
        context['grouped_entries'] = dict(grouped)

        # Get templates for invoice creation
        context['templates'] = settings.INVOICE_TEMPLATES
        available_templates = self.request.user.get_available_templates()
        context['available_templates'] = [
            (key, value['name'])
            for key, value in settings.INVOICE_TEMPLATES.items()
            if key in available_templates
        ]

        return context

    def post(self, request, *args, **kwargs):
        """Handle billing selected time entries."""
        company = self.get_company()
        if not company:
            messages.error(request, 'You need to create a company first.')
            return redirect('companies:create')

        # Get selected entry IDs
        entry_ids = request.POST.getlist('entries')
        if not entry_ids:
            messages.error(request, 'Please select at least one time entry to bill.')
            return redirect('invoices:bill_time')

        # Get billing options
        grouping = request.POST.get('grouping', 'detailed')
        template_style = request.POST.get('template_style', 'clean_slate')

        # Get selected entries
        entries = TimeEntry.objects.filter(
            id__in=entry_ids,
            company=company,
            status='unbilled',
            billable=True
        )

        if not entries.exists():
            messages.error(request, 'No valid entries selected.')
            return redirect('invoices:bill_time')

        # Check if user can create invoice
        if not request.user.can_create_invoice():
            messages.error(request, 'You have reached your invoice limit. Please upgrade your plan.')
            return redirect('billing:plans')

        # Use the time billing service
        from .services.time_billing import create_invoice_from_time_entries

        invoice = create_invoice_from_time_entries(
            entries=entries,
            company=company,
            user=request.user,
            grouping=grouping,
            template_style=template_style
        )

        if invoice:
            # Increment invoice count
            request.user.increment_invoice_count()
            messages.success(
                request,
                f'Invoice {invoice.invoice_number} created from {entries.count()} time entries.'
            )
            return redirect('invoices:detail', pk=invoice.pk)
        else:
            messages.error(request, 'Failed to create invoice from time entries.')
            return redirect('invoices:bill_time')


# Timer AJAX Views
@login_required
def timer_start(request):
    """Start a new timer."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    # Check if user can start a timer
    if not request.user.can_start_timer():
        max_timers = request.user.get_max_active_timers()
        return JsonResponse({
            'success': False,
            'error': f'You can only have {max_timers} active timer{"s" if max_timers != 1 else ""}. '
                     'Stop a timer before starting a new one.'
        }, status=400)

    company = request.user.get_company()
    if not company:
        return JsonResponse({
            'success': False,
            'error': 'You need to create a company first.'
        }, status=400)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    description = data.get('description', '').strip()
    client_email = data.get('client_email', '').strip()
    client_name = data.get('client_name', '').strip()

    # Get default hourly rate
    try:
        settings_obj = company.time_tracking_settings
        hourly_rate = settings_obj.default_hourly_rate
    except TimeTrackingSettings.DoesNotExist:
        from decimal import Decimal
        hourly_rate = Decimal('100.00')

    # Create the timer
    timer = ActiveTimer.objects.create(
        company=company,
        user=request.user,
        description=description,
        client_email=client_email,
        client_name=client_name,
        hourly_rate=hourly_rate
    )

    return JsonResponse({
        'success': True,
        'timer': {
            'id': timer.id,
            'description': timer.description,
            'started_at': timer.started_at.isoformat(),
            'elapsed_seconds': timer.elapsed_seconds,
            'hourly_rate': str(timer.hourly_rate),
        }
    })


@login_required
def timer_stop(request, timer_id):
    """Stop a timer and create a time entry."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    timer = get_object_or_404(ActiveTimer, id=timer_id, user=request.user)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    # Allow updating description before stopping
    description = data.get('description', '').strip()
    if description:
        timer.description = description
        timer.save(update_fields=['description'])

    # Stop the timer and create entry
    entry = timer.stop()

    return JsonResponse({
        'success': True,
        'entry': {
            'id': entry.id,
            'description': entry.description,
            'duration': entry.duration,
            'duration_display': entry.duration_display,
            'billable_amount': str(entry.billable_amount),
        }
    })


@login_required
def timer_discard(request, timer_id):
    """Discard a timer without saving."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    timer = get_object_or_404(ActiveTimer, id=timer_id, user=request.user)
    timer.discard()

    return JsonResponse({'success': True})


@login_required
def timer_status(request):
    """Get status of all active timers for the user."""
    timers = request.user.active_timers.all()

    timer_data = [{
        'id': t.id,
        'description': t.description,
        'client_name': t.client_name,
        'started_at': t.started_at.isoformat(),
        'elapsed_seconds': t.elapsed_seconds,
        'elapsed_display': t.elapsed_display,
        'hourly_rate': str(t.hourly_rate),
        'estimated_amount': str(t.estimated_amount),
    } for t in timers]

    return JsonResponse({
        'success': True,
        'timers': timer_data,
        'can_start_new': request.user.can_start_timer(),
        'max_timers': request.user.get_max_active_timers(),
    })
