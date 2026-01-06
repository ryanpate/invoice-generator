"""
Forms for invoices app.
"""
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from decimal import Decimal

from .models import Invoice, LineItem


class InvoiceForm(forms.ModelForm):
    """Form for creating/editing invoices."""

    class Meta:
        model = Invoice
        fields = [
            'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_date', 'payment_terms', 'currency', 'tax_rate',
            'notes', 'template_style'
        ]
        widgets = {
            'client_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Client or Company Name'
            }),
            'client_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'client@example.com'
            }),
            'client_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 123-4567'
            }),
            'client_address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Client address'
            }),
            'invoice_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'payment_terms': forms.Select(attrs={
                'class': 'form-select'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Payment instructions, thank you message, etc.'
            }),
            'template_style': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        # Set defaults from company
        if self.company and not self.instance.pk:
            self.initial['currency'] = self.company.default_currency
            self.initial['payment_terms'] = self.company.default_payment_terms
            self.initial['tax_rate'] = self.company.default_tax_rate
            self.initial['notes'] = self.company.default_notes
            self.initial['template_style'] = self.company.default_template

        # Limit template choices to user's available templates
        if self.user:
            available_templates = self.user.get_available_templates()
            template_choices = [
                (key, value['name'])
                for key, value in settings.INVOICE_TEMPLATES.items()
                if key in available_templates
            ]
            self.fields['template_style'].choices = template_choices


class LineItemForm(forms.ModelForm):
    """Form for invoice line items."""

    class Meta:
        model = LineItem
        fields = ['description', 'quantity', 'rate']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Service or product description'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input w-24',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '1'
            }),
            'rate': forms.NumberInput(attrs={
                'class': 'form-input w-32',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
        }


# Formset for managing multiple line items
LineItemFormSet = inlineformset_factory(
    Invoice,
    LineItem,
    form=LineItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class BatchUploadForm(forms.Form):
    """Form for batch CSV upload."""

    csv_file = forms.FileField(
        help_text='Upload a CSV file with invoice data',
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'hidden',
            'id': 'csv-file-input'
        })
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')

        if csv_file:
            # Check file size (max 10MB)
            if csv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('CSV file size must not exceed 10MB.')

            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError('Only CSV files are allowed.')

            # Check content type
            allowed_types = ['text/csv', 'application/vnd.ms-excel', 'text/plain']
            if hasattr(csv_file, 'content_type') and csv_file.content_type not in allowed_types:
                raise forms.ValidationError('Invalid file type. Please upload a CSV file.')

        return csv_file
