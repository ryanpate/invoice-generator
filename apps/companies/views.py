"""
Views for companies app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings

from .models import Company
from .forms import CompanyForm


class CompanySettingsView(LoginRequiredMixin, UpdateView):
    """Edit company settings."""
    model = Company
    form_class = CompanyForm
    template_name = 'settings/company.html'
    success_url = reverse_lazy('companies:settings')

    def get_object(self, queryset=None):
        """Get or create company for current user."""
        company, created = Company.objects.get_or_create(
            user=self.request.user,
            defaults={'name': f"{self.request.user.username}'s Company"}
        )
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = settings.INVOICE_TEMPLATES
        context['available_templates'] = self.request.user.get_available_templates()
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Company settings saved successfully!')
        return super().form_valid(form)


@login_required
def remove_logo(request):
    """Remove company logo."""
    if request.method == 'POST':
        try:
            company = request.user.company
            if company.logo:
                company.logo.delete()
                company.save()
                messages.success(request, 'Logo removed successfully.')
        except Company.DoesNotExist:
            pass

    return redirect('companies:settings')


@login_required
def remove_signature(request):
    """Remove company signature."""
    if request.method == 'POST':
        try:
            company = request.user.company
            if company.signature:
                company.signature.delete()
                company.save()
                messages.success(request, 'Signature removed successfully.')
        except Company.DoesNotExist:
            pass

    return redirect('companies:settings')
