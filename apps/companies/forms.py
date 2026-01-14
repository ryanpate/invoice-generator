"""
Forms for companies app.
"""
from django import forms
from django.conf import settings
from .models import Company


class CompanyForm(forms.ModelForm):
    """Form for editing company profile."""

    class Meta:
        model = Company
        fields = [
            'name', 'logo', 'signature', 'email', 'phone', 'website',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'tax_id',
            'default_currency', 'default_payment_terms', 'default_tax_rate',
            'default_template', 'default_notes', 'accent_color', 'invoice_prefix'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Company Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'billing@company.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 123-4567'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://www.company.com'
            }),
            'address_line1': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '123 Business Street'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Suite 100'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '12345'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'XX-XXXXXXX'
            }),
            'default_currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_payment_terms': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_tax_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'default_template': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Payment is due within 30 days...'
            }),
            'accent_color': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'color'
            }),
            'invoice_prefix': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'INV-'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Limit template choices to user's available templates
        if user:
            available_templates = user.get_available_templates()
            template_choices = [
                (key, value['name'])
                for key, value in settings.INVOICE_TEMPLATES.items()
                if key in available_templates
            ]
            self.fields['default_template'].choices = template_choices

    def clean_logo(self):
        """Validate logo file."""
        logo = self.cleaned_data.get('logo')
        if logo:
            # Check file size (max 5MB)
            if logo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Logo file size must not exceed 5MB.')

            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if hasattr(logo, 'content_type') and logo.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed.')

        return logo

    def clean_signature(self):
        """Validate signature file."""
        signature = self.cleaned_data.get('signature')
        if signature:
            # Check file size (max 2MB)
            if signature.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Signature file size must not exceed 2MB.')

            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if hasattr(signature, 'content_type') and signature.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed.')

        return signature
