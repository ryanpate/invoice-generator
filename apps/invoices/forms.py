"""
Forms for invoices app.
"""
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from decimal import Decimal

from .models import Invoice, LineItem, RecurringInvoice, RecurringLineItem, TimeEntry


class InvoiceForm(forms.ModelForm):
    """Form for creating/editing invoices."""

    # Override template_style as ChoiceField (CharField in model has no choices)
    template_style = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Invoice
        fields = [
            'invoice_name', 'client_name', 'client_email', 'client_phone', 'client_address',
            'invoice_date', 'payment_terms', 'currency', 'tax_rate',
            'notes', 'template_style'
        ]
        widgets = {
            'invoice_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Website Redesign Project (optional)'
            }),
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
            # Fallback to clean_slate if no templates available
            if not template_choices:
                template_choices = [('clean_slate', 'Clean Slate')]
            self.fields['template_style'].choices = template_choices
        else:
            # Default choices if no user
            self.fields['template_style'].choices = [
                (key, value['name'])
                for key, value in settings.INVOICE_TEMPLATES.items()
            ]


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


class SendInvoiceEmailForm(forms.Form):
    """Form for sending invoice via email."""

    to_email = forms.EmailField(
        label='To',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'client@example.com'
        })
    )

    cc_emails = forms.CharField(
        label='CC (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'cc1@example.com, cc2@example.com'
        }),
        help_text='Separate multiple emails with commas'
    )

    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Invoice from Your Company'
        })
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 6,
            'placeholder': 'Please find attached your invoice...'
        })
    )

    def clean_cc_emails(self):
        """Validate CC email addresses."""
        cc_string = self.cleaned_data.get('cc_emails', '')
        if not cc_string:
            return []

        emails = [e.strip() for e in cc_string.split(',') if e.strip()]
        for email in emails:
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError:
                raise forms.ValidationError(f'Invalid email address: {email}')
        return emails


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


class RecurringInvoiceForm(forms.ModelForm):
    """Form for creating/editing recurring invoices."""

    template_style = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = RecurringInvoice
        fields = [
            'name', 'client_name', 'client_email', 'client_phone', 'client_address',
            'frequency', 'start_date', 'end_date',
            'currency', 'payment_terms', 'tax_rate',
            'template_style', 'notes',
            'send_email_on_generation', 'auto_send_to_client'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Monthly Retainer - Acme Corp'
            }),
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
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_terms': forms.Select(attrs={
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
            'send_email_on_generation': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'auto_send_to_client': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
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
            if not template_choices:
                template_choices = [('clean_slate', 'Clean Slate')]
            self.fields['template_style'].choices = template_choices
        else:
            self.fields['template_style'].choices = [
                (key, value['name'])
                for key, value in settings.INVOICE_TEMPLATES.items()
            ]


class RecurringLineItemForm(forms.ModelForm):
    """Form for recurring invoice line items."""

    class Meta:
        model = RecurringLineItem
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


# Formset for recurring invoice line items
RecurringLineItemFormSet = inlineformset_factory(
    RecurringInvoice,
    RecurringLineItem,
    form=RecurringLineItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class TimeEntryForm(forms.ModelForm):
    """Form for creating/editing time entries."""

    # Use hours and minutes inputs that convert to duration in seconds
    hours = forms.IntegerField(
        min_value=0,
        max_value=999,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-20',
            'placeholder': '0',
            'min': '0',
        })
    )
    minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-20',
            'placeholder': '0',
            'min': '0',
            'max': '59',
        })
    )

    class Meta:
        model = TimeEntry
        fields = [
            'description', 'client_name', 'client_email',
            'date', 'hourly_rate', 'billable'
        ]
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What did you work on?'
            }),
            'client_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Client name (optional)'
            }),
            'client_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'client@example.com (optional)'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '100.00'
            }),
            'billable': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        # Set default hourly rate from company settings
        if self.company and not self.instance.pk:
            try:
                settings_obj = self.company.time_tracking_settings
                self.initial['hourly_rate'] = settings_obj.default_hourly_rate
            except Exception:
                self.initial['hourly_rate'] = Decimal('100.00')

        # If editing, populate hours/minutes from duration
        if self.instance.pk and self.instance.duration:
            hours, remainder = divmod(self.instance.duration, 3600)
            minutes = remainder // 60
            self.initial['hours'] = hours
            self.initial['minutes'] = minutes

    def clean(self):
        cleaned_data = super().clean()
        hours = cleaned_data.get('hours', 0) or 0
        minutes = cleaned_data.get('minutes', 0) or 0

        # Calculate duration in seconds
        duration = (hours * 3600) + (minutes * 60)

        if duration == 0:
            raise forms.ValidationError('Duration must be greater than 0.')

        cleaned_data['duration'] = duration
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duration = self.cleaned_data.get('duration', 0)
        if commit:
            instance.save()
        return instance
