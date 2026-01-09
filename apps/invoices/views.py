"""
Views for invoices app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db.models import Q
from django.conf import settings

from .models import Invoice, LineItem, InvoiceBatch, RecurringInvoice
from .forms import (
    InvoiceForm, LineItemFormSet, BatchUploadForm, SendInvoiceEmailForm,
    RecurringInvoiceForm, RecurringLineItemFormSet
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


class InvoiceSendEmailView(LoginRequiredMixin, FormView):
    """View for sending invoice via email."""
    template_name = 'invoices/send_email.html'
    form_class = SendInvoiceEmailForm

    def dispatch(self, request, *args, **kwargs):
        # Let LoginRequiredMixin handle authentication first
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # Get invoice after confirming user is authenticated
        self.invoice = get_object_or_404(
            Invoice,
            pk=self.kwargs['pk'],
            company__user=request.user
        )
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

class RecurringInvoiceListView(LoginRequiredMixin, ListView):
    """List all recurring invoices for the current user."""
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
        queryset = RecurringInvoice.objects.filter(
            company__user=self.request.user
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


class RecurringInvoiceDetailView(LoginRequiredMixin, DetailView):
    """View recurring invoice details."""
    model = RecurringInvoice
    template_name = 'invoices/recurring/detail.html'
    context_object_name = 'recurring'

    def get_queryset(self):
        return RecurringInvoice.objects.filter(
            company__user=self.request.user
        ).select_related('company', 'last_invoice').prefetch_related('line_items')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get generated invoices
        context['generated_invoices'] = Invoice.objects.filter(
            invoice_name=self.object.name,
            company=self.object.company
        ).order_by('-created_at')[:10]
        return context


class RecurringInvoiceCreateView(LoginRequiredMixin, CreateView):
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
        kwargs['company'] = getattr(self.request.user, 'company', None)
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

        # Get or create company
        from apps.companies.models import Company
        company, _ = Company.objects.get_or_create(
            user=self.request.user,
            defaults={'name': f"{self.request.user.username}'s Company"}
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


class RecurringInvoiceUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing recurring invoice."""
    model = RecurringInvoice
    form_class = RecurringInvoiceForm
    template_name = 'invoices/recurring/edit.html'

    def get_queryset(self):
        return RecurringInvoice.objects.filter(company__user=self.request.user)

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


class RecurringInvoiceDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a recurring invoice."""
    model = RecurringInvoice
    template_name = 'invoices/recurring/delete_confirm.html'
    success_url = reverse_lazy('invoices:recurring_list')

    def get_queryset(self):
        return RecurringInvoice.objects.filter(company__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Recurring invoice deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def recurring_toggle_status(request, pk):
    """Toggle recurring invoice status between active and paused."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    recurring = get_object_or_404(
        RecurringInvoice,
        pk=pk,
        company__user=request.user
    )

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

    recurring = get_object_or_404(
        RecurringInvoice,
        pk=pk,
        company__user=request.user
    )

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
