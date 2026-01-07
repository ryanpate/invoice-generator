"""
Views for invoices app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db.models import Q
from django.conf import settings

from .models import Invoice, LineItem, InvoiceBatch
from .forms import InvoiceForm, LineItemFormSet, BatchUploadForm
# PDF generator imported lazily to avoid WeasyPrint startup issues
from .services.batch_processor import BatchInvoiceProcessor, get_csv_template


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


class InvoiceListView(LoginRequiredMixin, ListView):
    """List all invoices for the current user."""
    model = Invoice
    template_name = 'invoices/list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        queryset = Invoice.objects.filter(
            company__user=self.request.user
        ).select_related('company')

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


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View single invoice details."""
    model = Invoice
    template_name = 'invoices/detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        return Invoice.objects.filter(
            company__user=self.request.user
        ).prefetch_related('line_items')


class InvoiceCreateView(LoginRequiredMixin, CreateView):
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
        kwargs['company'] = getattr(self.request.user, 'company', None)
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

        # Get or create company
        from apps.companies.models import Company
        company, _ = Company.objects.get_or_create(
            user=self.request.user,
            defaults={'name': f"{self.request.user.username}'s Company"}
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


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing invoice."""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoices/edit.html'

    def get_queryset(self):
        return Invoice.objects.filter(company__user=self.request.user)

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


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an invoice."""
    model = Invoice
    template_name = 'invoices/delete_confirm.html'
    success_url = reverse_lazy('invoices:list')

    def get_queryset(self):
        return Invoice.objects.filter(company__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Invoice deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def generate_pdf(request, pk):
    """Generate PDF for an invoice."""
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        company__user=request.user
    )

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
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        company__user=request.user
    )

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


class BatchUploadView(LoginRequiredMixin, TemplateView):
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
        context['recent_batches'] = InvoiceBatch.objects.filter(
            company__user=self.request.user
        ).order_by('-created_at')[:5]
        return context

    def post(self, request, *args, **kwargs):
        form = BatchUploadForm(request.POST, request.FILES)

        if form.is_valid():
            # Get or create company
            from apps.companies.models import Company
            company, _ = Company.objects.get_or_create(
                user=request.user,
                defaults={'name': f"{request.user.username}'s Company"}
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


class BatchResultView(LoginRequiredMixin, DetailView):
    """View batch processing results."""
    model = InvoiceBatch
    template_name = 'invoices/batch_result.html'
    context_object_name = 'batch'

    def get_queryset(self):
        return InvoiceBatch.objects.filter(company__user=self.request.user)


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
    batch = get_object_or_404(
        InvoiceBatch,
        pk=pk,
        company__user=request.user
    )

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

    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        company__user=request.user
    )

    valid_statuses = [s[0] for s in Invoice.STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    invoice.status = status
    invoice.save(update_fields=['status', 'updated_at'])

    messages.success(request, f'Invoice marked as {status}.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'status': status})

    return redirect('invoices:detail', pk=pk)
