from django import forms
from .models import AffiliateApplication


class AffiliateApplicationForm(forms.ModelForm):
    """Form for applying to the affiliate program."""

    class Meta:
        model = AffiliateApplication
        fields = ['website', 'audience_size', 'promotion_methods']
        widgets = {
            'website': forms.URLInput(attrs={
                'class': 'form-input w-full dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                'placeholder': 'https://yourwebsite.com or social media profile'
            }),
            'audience_size': forms.TextInput(attrs={
                'class': 'form-input w-full dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                'placeholder': 'e.g., 5,000 email subscribers, 10K Instagram followers'
            }),
            'promotion_methods': forms.Textarea(attrs={
                'class': 'form-input w-full dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                'rows': 4,
                'placeholder': 'Describe how you plan to promote InvoiceKits (blog posts, social media, email newsletter, YouTube, etc.)'
            }),
        }
        labels = {
            'website': 'Website or Social Profile',
            'audience_size': 'Audience Size',
            'promotion_methods': 'Promotion Plan',
        }
        help_texts = {
            'website': 'Your website, blog, or primary social media profile.',
            'audience_size': 'Approximate size of your audience (followers, subscribers, etc.).',
            'promotion_methods': 'Tell us how you plan to promote InvoiceKits to your audience.',
        }
