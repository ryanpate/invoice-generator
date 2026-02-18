# Voice-to-Invoice Promotion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote the Voice-to-Invoice feature on the landing page, SEO meta tags, and a new `/features/voice-invoice/` landing page.

**Architecture:** Add a `VoiceInvoiceView(TemplateView)` alongside the existing `AIInvoiceGeneratorView` and `TimeTrackingView` in `apps/invoices/views.py`. Wire it in `apps/invoices/urls_public.py` and add to sitemap. Update the landing page hero + highlight cards + features grid. Add cross-links to both existing feature pages.

**Tech Stack:** Django TemplateView, Tailwind CSS (CDN), JSON-LD structured data (BreadcrumbList, HowTo, FAQPage, SoftwareApplication), Django i18n `{% trans %}` tags.

---

## Task 1: Add view + URL + sitemap

**Files:**
- Modify: `apps/invoices/views.py` (after line 135, `TimeTrackingView`)
- Modify: `apps/invoices/urls_public.py` (line 22, after time-tracking URL)
- Modify: `config/urls.py` (line 43, `StaticViewSitemap.items()` list)

**Step 1: Add the view class**

In `apps/invoices/views.py`, after the `TimeTrackingView` class (after line 135), insert:

```python
class VoiceInvoiceView(TemplateView):
    """Landing page for Voice-to-Invoice feature."""
    template_name = 'features/voice-invoice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = settings.SUBSCRIPTION_TIERS
        context['ai_limits'] = settings.AI_GENERATION_LIMITS
        return context
```

**Step 2: Wire the URL**

In `apps/invoices/urls_public.py`, after line 22 (time-tracking URL), add:

```python
path('features/voice-invoice/', views.VoiceInvoiceView.as_view(), name='feature_voice_invoice'),
```

**Step 3: Add to sitemap**

In `config/urls.py`, in `StaticViewSitemap.items()` (line 43), change:

```python
'/features/ai-invoice-generator/', '/features/time-tracking/',
```

to:

```python
'/features/ai-invoice-generator/', '/features/time-tracking/', '/features/voice-invoice/',
```

**Step 4: Verify the URL resolves**

```bash
cd /Users/ryanpate/invoice-generator
source .venv/bin/activate
python manage.py shell -c "from django.urls import reverse; print(reverse('feature_voice_invoice'))"
```

Expected output: `/features/voice-invoice/`

**Step 5: Commit**

```bash
git add apps/invoices/views.py apps/invoices/urls_public.py config/urls.py
git commit -m "feat: add VoiceInvoiceView, URL, and sitemap entry"
```

---

## Task 2: Create the voice-invoice feature page template

**Files:**
- Create: `templates/features/voice-invoice.html`

Model closely on `templates/features/ai-invoice-generator.html`. Key differences: blue/indigo colour scheme (not purple), mic icon instead of sparkle, CTA points to `/try/` (voice is live there without signup) in addition to signup.

**Step 1: Create the file**

Create `templates/features/voice-invoice.html` with this content:

```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}Voice Invoice Generator - Create Invoices by Speaking | InvoiceKits{% endblock %}

{% block meta_description %}Create professional invoices by voice. Just tap the mic, describe your work out loud, and our AI instantly fills your invoice. No typing needed. Free to try.{% endblock %}

{% block meta_keywords %}voice invoice generator, voice to invoice, dictate invoice, speech to invoice, voice billing, ai voice invoice, speak invoice{% endblock %}

{% block canonical_url %}https://www.invoicekits.com/features/voice-invoice/{% endblock %}

{% block og_title %}Voice Invoice Generator - Create Invoices by Speaking | InvoiceKits{% endblock %}

{% block og_description %}Tap the mic, describe your work, get a filled invoice. Our AI transcribes your voice and extracts client details, line items, and rates automatically.{% endblock %}

{% block twitter_title %}Voice Invoice Generator | InvoiceKits{% endblock %}

{% block twitter_description %}Create invoices by speaking. Tap mic, describe your work, get a filled invoice. Powered by Claude AI.{% endblock %}

{% block extra_schema %}
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": "https://www.invoicekits.com/"
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "Features",
            "item": "https://www.invoicekits.com/features/"
        },
        {
            "@type": "ListItem",
            "position": 3,
            "name": "Voice Invoice Generator",
            "item": "https://www.invoicekits.com/features/voice-invoice/"
        }
    ]
}
</script>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "HowTo",
    "name": "How to Create an Invoice by Voice",
    "description": "Use InvoiceKits voice invoice generator to create a professional invoice by speaking. Claude AI transcribes your audio and extracts all invoice fields automatically.",
    "totalTime": "PT1M",
    "estimatedCost": {
        "@type": "MonetaryAmount",
        "currency": "USD",
        "value": "0"
    },
    "tool": {
        "@type": "HowToTool",
        "name": "InvoiceKits Voice Invoice Generator"
    },
    "step": [
        {
            "@type": "HowToStep",
            "position": 1,
            "name": "Tap the Mic",
            "text": "Open the AI Generate section on any invoice and click the microphone button. Your browser will ask for microphone permission — allow it."
        },
        {
            "@type": "HowToStep",
            "position": 2,
            "name": "Speak Your Invoice Details",
            "text": "Describe your work out loud. Include the client name, what you did, hours or fixed price, and any other details. For example: 'Invoice for Acme Corp. Website redesign, 15 hours at 100 dollars an hour. Payment due in 30 days.'"
        },
        {
            "@type": "HowToStep",
            "position": 3,
            "name": "Apply to Your Invoice",
            "text": "Review the transcript and extracted fields, then click Apply to Invoice. All fields — client name, email, line items, rates, and payment terms — are filled in automatically."
        }
    ]
}
</script>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {
            "@type": "Question",
            "name": "What is a voice invoice generator?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "A voice invoice generator lets you create invoices by speaking instead of typing. You tap a microphone button, describe your work and client details out loud, and AI automatically transcribes your speech and fills in the invoice fields — including client name, email, line items, rates, and payment terms."
            }
        },
        {
            "@type": "Question",
            "name": "What details can I dictate by voice?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "InvoiceKits Voice Invoice Generator can extract: client name, client email, client address, invoice currency, payment terms (e.g. Net 30), and all line items with descriptions, quantities, and rates. Just speak naturally and the AI figures out the structure."
            }
        },
        {
            "@type": "Question",
            "name": "Is the voice invoice generator free?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes! You can try it on the /try/ page without signing up. Voice generation shares the same AI quota as text generation: Free users get 3 generations/month, Starter gets 10, and Professional and Business plans include unlimited generations."
            }
        },
        {
            "@type": "Question",
            "name": "What browsers support voice invoicing?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Voice invoicing requires browser support for the MediaRecorder API. It works in Chrome, Edge, Firefox, and Safari on desktop. On mobile, it works in Chrome for Android and Safari for iOS. The mic button is automatically hidden on unsupported browsers."
            }
        },
        {
            "@type": "Question",
            "name": "How long can my voice recording be?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Recordings are limited to 60 seconds. A warning appears at 55 seconds and recording stops automatically at 60 seconds. This is more than enough to describe even a complex multi-line invoice."
            }
        }
    ]
}
</script>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "InvoiceKits Voice Invoice Generator",
    "applicationCategory": "BusinessApplication",
    "operatingSystem": "Web",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD",
        "description": "Free tier includes 3 voice invoice generations per month"
    },
    "featureList": [
        "Voice-to-invoice transcription",
        "Automatic field extraction (client name, email, address, payment terms)",
        "Multi-line item detection",
        "Hourly rate and fixed price parsing",
        "60-second max recording",
        "Preview before applying",
        "Works without signup on /try/"
    ]
}
</script>
{% endblock %}

{% block content %}
<!-- Hero Section -->
<section class="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 overflow-hidden">
    <div class="absolute inset-0 bg-grid-white/[0.05] bg-[size:20px_20px]"></div>
    <div class="absolute top-20 left-10 w-72 h-72 bg-blue-500/30 rounded-full blur-3xl"></div>
    <div class="absolute bottom-10 right-10 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl"></div>

    <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <!-- Breadcrumb -->
        <nav class="mb-8">
            <ol class="flex items-center space-x-2 text-sm text-blue-200">
                <li><a href="{% url 'landing' %}" class="hover:text-white">Home</a></li>
                <li><span class="mx-2">/</span></li>
                <li><span>Features</span></li>
                <li><span class="mx-2">/</span></li>
                <li class="text-white">Voice Invoice Generator</li>
            </ol>
        </nav>

        <div class="grid lg:grid-cols-2 gap-12 items-center">
            <div>
                <div class="flex items-center gap-3 mb-6">
                    <span class="inline-flex items-center px-4 py-1 bg-blue-500/30 text-blue-100 rounded-full text-sm font-medium">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                        </svg>
                        Powered by Claude AI
                    </span>
                    <span class="inline-flex items-center px-3 py-1 bg-green-500/30 text-green-100 rounded-full text-xs font-medium">
                        NEW
                    </span>
                </div>
                <h1 class="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                    Invoice by Voice.<br>No Typing Required.
                </h1>
                <p class="text-xl md:text-2xl text-blue-100 mb-4">
                    Tap the mic. Speak your work. Get a filled invoice.
                </p>
                <p class="text-lg text-blue-200 mb-8">
                    Just say "Invoice for Acme Corp — website redesign, 15 hours at $100 per hour, Net 30" and Claude fills every field automatically. Client name, email, line items, payment terms — all extracted from your voice.
                </p>
                <div class="flex flex-col sm:flex-row gap-4">
                    <a href="{% url 'try_invoice' %}" class="px-8 py-4 bg-white text-blue-700 font-semibold rounded-lg hover:bg-gray-100 transition shadow-lg text-center">
                        Try Voice Invoicing Free
                    </a>
                    <a href="#how-it-works" class="px-8 py-4 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition text-center">
                        See How It Works
                    </a>
                </div>
                <p class="mt-6 text-blue-200 text-sm">
                    No signup required on the Try page. 3 free voice generations/month after signup.
                </p>
            </div>

            <!-- Voice Demo Visual -->
            <div class="hidden lg:block">
                <div class="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-2xl">
                    <div class="flex items-center gap-2 mb-4">
                        <div class="w-3 h-3 rounded-full bg-red-400"></div>
                        <div class="w-3 h-3 rounded-full bg-yellow-400"></div>
                        <div class="w-3 h-3 rounded-full bg-green-400"></div>
                        <span class="ml-2 text-white/60 text-sm">Voice Invoice Generator</span>
                    </div>

                    <!-- Mic button -->
                    <div class="bg-white/5 rounded-lg p-4 mb-4 border border-white/10 flex items-center gap-4">
                        <div class="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg">
                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="text-white font-medium text-sm">Recording...</p>
                            <p class="text-blue-200 text-xs font-mono">"Invoice for Acme Corp. Website redesign, 15 hours at $100 per hour. Net 30 payment terms."</p>
                        </div>
                    </div>

                    <!-- Arrow -->
                    <div class="flex justify-center my-4">
                        <div class="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center animate-bounce">
                            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
                            </svg>
                        </div>
                    </div>

                    <!-- Extracted fields -->
                    <div class="bg-white rounded-lg p-4">
                        <p class="text-gray-600 text-sm mb-3 font-medium">Extracted Invoice Fields:</p>
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between items-center py-1 border-b border-gray-100">
                                <span class="text-gray-500">Client</span>
                                <span class="font-medium text-gray-900">Acme Corp</span>
                            </div>
                            <div class="flex justify-between items-center py-1 border-b border-gray-100">
                                <span class="text-gray-500">Payment Terms</span>
                                <span class="font-medium text-gray-900">Net 30</span>
                            </div>
                            <div class="flex justify-between items-center py-1 border-b border-gray-100">
                                <span class="text-gray-500">Website Redesign</span>
                                <span class="font-medium text-gray-900">$1,500.00</span>
                            </div>
                            <div class="text-xs text-gray-400">15 hrs @ $100/hr</div>
                            <div class="flex justify-between items-center pt-2">
                                <span class="font-bold text-gray-900">Total</span>
                                <span class="font-bold text-blue-600 text-lg">$1,500.00</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Problem/Solution Section -->
<section class="py-16 bg-gray-50 dark:bg-gray-900">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-4">Your Hands Are Full. Your Invoice Shouldn't Be.</h2>
            <p class="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                Whether you're wrapping up a job site, leaving a client meeting, or just finished a call — voice lets you capture the invoice before you forget the details.
            </p>
        </div>

        <div class="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <!-- Before -->
            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 border-l-4 border-red-400">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                        <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">The Old Way</h3>
                </div>
                <ul class="space-y-3 text-gray-600 dark:text-gray-300">
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                        Open laptop, navigate to invoicing tool
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                        Type client name, email, address manually
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                        Enter each line item description separately
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                        Forget exactly what you discussed
                    </li>
                </ul>
                <p class="mt-4 text-sm text-red-600 dark:text-red-400 font-medium">Average time: 15–30 minutes per invoice</p>
            </div>

            <!-- After -->
            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 border-l-4 border-green-400">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">With Voice Invoicing</h3>
                </div>
                <ul class="space-y-3 text-gray-600 dark:text-gray-300">
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                        Tap mic — it works on phone, tablet, or desktop
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                        Speak naturally for up to 60 seconds
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                        AI fills client, items, rates, and payment terms
                    </li>
                    <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                        Review and send while the details are fresh
                    </li>
                </ul>
                <p class="mt-4 text-sm text-green-600 dark:text-green-400 font-medium">Average time: Under 60 seconds</p>
            </div>
        </div>
    </div>
</section>

<!-- How It Works Section -->
<section id="how-it-works" class="py-20 bg-white dark:bg-gray-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
            <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-4">How Voice Invoicing Works</h2>
            <p class="text-xl text-gray-600 dark:text-gray-300">Three steps from speaking to a ready-to-send invoice</p>
        </div>

        <div class="grid md:grid-cols-3 gap-8">
            <!-- Step 1 -->
            <div class="relative bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <div class="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-6 text-white font-bold text-2xl">1</div>
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">Tap the Mic</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-4">
                    Open the AI Generate section on any invoice page and click the microphone button. Grant browser microphone permission when prompted.
                </p>
                <div class="bg-white dark:bg-gray-600 rounded-lg p-4 flex items-center justify-center">
                    <div class="w-14 h-14 bg-blue-500 rounded-full flex items-center justify-center shadow-lg">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                        </svg>
                    </div>
                </div>
            </div>

            <!-- Step 2 -->
            <div class="relative bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <div class="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-6 text-white font-bold text-2xl">2</div>
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">Speak Your Invoice</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-4">
                    Say the client name, what work you did, hours or fixed price, and any other details. Speak naturally for up to 60 seconds.
                </p>
                <div class="bg-white dark:bg-gray-600 rounded-lg p-4 text-sm font-mono text-gray-700 dark:text-gray-200 text-center">
                    "Invoice for Acme Corp. Website redesign, 15 hours at $100 per hour. Net 30 payment terms."
                </div>
            </div>

            <!-- Step 3 -->
            <div class="relative bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <div class="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-6 text-white font-bold text-2xl">3</div>
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">Apply to Invoice</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-4">
                    Review the transcript and extracted fields. Click "Apply to Invoice" and all detected fields are filled in. Only empty fields are populated — existing values are never overwritten.
                </p>
                <div class="flex gap-2">
                    <button class="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg">Apply to Invoice</button>
                    <button class="px-4 py-2 border border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-200 text-sm font-medium rounded-lg">Edit</button>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- What Gets Extracted Section -->
<section class="py-20 bg-gray-50 dark:bg-gray-900">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
            <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-4">Everything Claude Extracts From Your Voice</h2>
            <p class="text-xl text-gray-600 dark:text-gray-300">One recording fills the entire invoice form</p>
        </div>

        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Client Details</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Name, email address, and mailing address — all parsed from natural speech.</p>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Line Items</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Multiple work items with descriptions, quantities, and rates — all generated in one recording.</p>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Payment Terms</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Net 30, Net 15, Due on Receipt — just say it and it's set.</p>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Currency</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Mention "euros", "pounds", or "CAD" and the currency is set automatically.</p>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Hourly & Fixed Rates</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Both "8 hours at $120/hour" and "fixed fee of $800" are understood and structured correctly.</p>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
                <div class="w-12 h-12 bg-pink-100 dark:bg-pink-900/30 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-pink-600 dark:text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Safe Application</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Only empty fields are filled. If you've already entered a client name, voice won't overwrite it.</p>
            </div>
        </div>
    </div>
</section>

<!-- FAQ Section -->
<section class="py-20 bg-white dark:bg-gray-800">
    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-4">Frequently Asked Questions</h2>
        </div>

        <div class="space-y-6">
            <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">What is a voice invoice generator?</h3>
                <p class="text-gray-600 dark:text-gray-300">A voice invoice generator lets you create invoices by speaking instead of typing. You tap a microphone button, describe your work and client details out loud, and AI automatically transcribes your speech and fills in the invoice fields — including client name, email, line items, rates, and payment terms.</p>
            </div>

            <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">What invoice details can I dictate by voice?</h3>
                <p class="text-gray-600 dark:text-gray-300">InvoiceKits can extract: client name, client email, client address, invoice currency, payment terms (e.g. Net 30), and all line items with descriptions, quantities, and rates. Just speak naturally and the AI figures out the structure.</p>
            </div>

            <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">Is the voice invoice generator free?</h3>
                <p class="text-gray-600 dark:text-gray-300">Yes! You can try it on the <a href="{% url 'try_invoice' %}" class="text-blue-600 dark:text-blue-400 underline">/try/ page</a> without signing up. Voice generation shares the same AI quota as text generation: Free users get 3 generations/month, Starter gets 10, and Professional and Business plans include unlimited generations.</p>
            </div>

            <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">What browsers support voice invoicing?</h3>
                <p class="text-gray-600 dark:text-gray-300">Voice invoicing requires browser support for the MediaRecorder API. It works in Chrome, Edge, Firefox, and Safari on desktop. On mobile, it works in Chrome for Android and Safari for iOS. The mic button is automatically hidden on unsupported browsers.</p>
            </div>

            <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-6">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">How long can my voice recording be?</h3>
                <p class="text-gray-600 dark:text-gray-300">Recordings are limited to 60 seconds. A warning appears at 55 seconds and recording stops automatically at 60 seconds. This is more than enough to describe even a complex multi-line invoice.</p>
            </div>
        </div>
    </div>
</section>

<!-- Related Features -->
<section class="py-16 bg-gray-50 dark:bg-gray-900">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-10">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Pair With Our Other AI Features</h2>
            <p class="text-gray-600 dark:text-gray-300">Voice invoicing is part of a complete AI-powered invoicing suite</p>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
            <!-- AI Invoice Generator -->
            <a href="{% url 'feature_ai_invoice_generator' %}" class="block group">
                <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 border-2 border-purple-200 dark:border-purple-800 hover:border-purple-400 dark:hover:border-purple-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-purple-700 dark:group-hover:text-purple-400 transition-colors">AI Invoice Generator</h3>
                                <span class="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-xs font-medium rounded">BETA</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm">Prefer typing? Describe your work in plain English — AI generates structured line items instantly.</p>
                            <span class="inline-flex items-center text-purple-600 dark:text-purple-400 text-sm font-medium mt-2 group-hover:translate-x-1 transition-transform">
                                Learn more
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>

            <!-- Time Tracking -->
            <a href="{% url 'feature_time_tracking' %}" class="block group">
                <div class="bg-white dark:bg-gray-800 rounded-2xl p-6 border-2 border-cyan-200 dark:border-cyan-800 hover:border-cyan-400 dark:hover:border-cyan-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-cyan-100 dark:bg-cyan-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-cyan-700 dark:group-hover:text-cyan-400 transition-colors">Built-In Time Tracking</h3>
                                <span class="px-2 py-0.5 bg-cyan-100 dark:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300 text-xs font-medium rounded">NEW</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm">Track billable hours with a live timer. Convert time entries to invoices with one click.</p>
                            <span class="inline-flex items-center text-cyan-600 dark:text-cyan-400 text-sm font-medium mt-2 group-hover:translate-x-1 transition-transform">
                                Learn more
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>
        </div>
    </div>
</section>

<!-- Final CTA -->
<section class="py-20 bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div class="inline-flex items-center px-4 py-1 bg-blue-500/30 text-blue-100 rounded-full text-sm font-medium mb-6">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
            </svg>
            Voice-Powered Invoicing
        </div>
        <h2 class="text-3xl md:text-4xl font-bold text-white mb-6">
            Your Next Invoice Takes 60 Seconds.
        </h2>
        <p class="text-xl text-blue-100 mb-8">
            No typing. No forms. Just speak and send.
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="{% url 'try_invoice' %}" class="inline-block px-8 py-4 bg-white text-blue-700 font-semibold rounded-lg hover:bg-gray-100 transition shadow-lg">
                Try Voice Invoicing — No Signup
            </a>
            <a href="{% url 'account_signup' %}" class="inline-block px-8 py-4 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition">
                Create Free Account
            </a>
        </div>
        <p class="mt-6 text-blue-200 text-sm">
            3 free voice generations/month. No credit card required.
        </p>
    </div>
</section>
{% endblock %}
```

**Step 2: Verify the template renders (start dev server)**

```bash
source .venv/bin/activate
python manage.py runserver
```

Open http://127.0.0.1:8000/features/voice-invoice/ and verify:
- Page loads without errors
- Hero section visible with blue/indigo gradient
- Breadcrumb shows Home / Features / Voice Invoice Generator
- All 3 how-it-works steps visible
- Related features section shows AI and Time Tracking links
- Final CTA has two buttons (Try No Signup + Create Account)

**Step 3: Commit**

```bash
git add templates/features/voice-invoice.html
git commit -m "feat: add voice-invoice feature landing page"
```

---

## Task 3: Update the landing page

**Files:**
- Modify: `templates/landing/index.html`

**Step 1: Update meta title (line 4)**

Change:
```html
{% block title %}{% trans "Free Invoice Generator — Create & Download PDF Invoices Instantly" %} | InvoiceKits{% endblock %}
```

To:
```html
{% block title %}{% trans "Voice Invoice Generator — Create Invoices by Speaking | Free AI Invoicing" %} | InvoiceKits{% endblock %}
```

**Step 2: Update meta description (line 6)**

Change:
```html
{% block meta_description %}{% trans "Create professional PDF invoices in under 60 seconds — no signup required. Add line items, tax, and notes, then download or email your invoice. Try it free now." %}{% endblock %}
```

To:
```html
{% block meta_description %}{% trans "Create professional invoices by voice or AI text — no signup required. Tap the mic, describe your work, and download your PDF invoice in seconds. Free to try." %}{% endblock %}
```

**Step 3: Update meta keywords (line 8)**

Change:
```html
{% block meta_keywords %}{% trans "ai invoice generator, time tracking invoice software, free invoice maker, ai billing software, invoice time tracker, automated invoice creation, freelancer invoice generator" %}{% endblock %}
```

To:
```html
{% block meta_keywords %}{% trans "voice invoice generator, ai invoice generator, voice to invoice, dictate invoice, time tracking invoice software, free invoice maker, ai billing software, invoice time tracker" %}{% endblock %}
```

**Step 4: Update the hero H1 (lines 18–21)**

Change:
```html
<h1 class="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
    {% trans "AI-Powered Invoice Generator" %}<br>
    <span class="text-primary-200">{% trans "With Built-In Time Tracking" %}</span>
</h1>
```

To:
```html
<h1 class="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
    {% trans "AI-Powered Invoice Generator" %}<br>
    <span class="text-primary-200">{% trans "With Voice, Text & Time Tracking" %}</span>
</h1>
```

**Step 5: Update hero description (lines 22–24)**

Change:
```html
<p class="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
    {% trans "The smartest invoice generator for freelancers and small businesses. Describe your work in plain English and let AI generate your invoice. Track billable hours with our live timer. Create professional PDF invoices instantly." %}
</p>
```

To:
```html
<p class="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
    {% trans "The smartest invoice generator for freelancers and small businesses. Tap the mic and dictate your invoice — or type in plain English. Track billable hours with our live timer. Create professional PDF invoices instantly." %}
</p>
```

**Step 6: Expand the 2-card highlight section to 3 cards (lines 54–111)**

The section currently has `<div class="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">`.

Change that opening `<div>` from `md:grid-cols-2` to `md:grid-cols-3`, and insert a new middle Voice card between the AI card and Time Tracking card.

Replace the entire grid div and its contents (lines 54–111):

```html
<div class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
    <!-- AI Invoice Generator Card -->
    <a href="{% url 'feature_ai_invoice_generator' %}" class="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-700 p-8 text-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
        <div class="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
        <div class="absolute bottom-0 left-0 -mb-8 -ml-8 w-40 h-40 bg-purple-400/20 rounded-full blur-3xl"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                    </svg>
                </div>
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-white/20 backdrop-blur-sm">
                    {% trans "BETA" %}
                </span>
            </div>
            <h3 class="text-2xl font-bold mb-3">{% trans "AI Invoice Generator" %}</h3>
            <p class="text-purple-100 mb-6">
                {% trans "Describe your work in plain English — \"Built React dashboard, 12 hours at $150/hr\" — and our AI instantly creates invoice line items. No more manual data entry." %}
            </p>
            <div class="flex items-center text-white font-medium group-hover:translate-x-2 transition-transform">
                {% trans "Learn More" %}
                <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
            </div>
        </div>
    </a>

    <!-- Voice Invoice Card (NEW) -->
    <a href="{% url 'feature_voice_invoice' %}" class="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 p-8 text-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
        <div class="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
        <div class="absolute bottom-0 left-0 -mb-8 -ml-8 w-40 h-40 bg-blue-400/20 rounded-full blur-3xl"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                    </svg>
                </div>
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-white/20 backdrop-blur-sm">
                    {% trans "NEW" %}
                </span>
            </div>
            <h3 class="text-2xl font-bold mb-3">{% trans "Voice-to-Invoice" %}</h3>
            <p class="text-blue-100 mb-6">
                {% trans "Tap the mic and dictate — \"Invoice for Acme Corp, website redesign, 15 hours at $100/hr, Net 30\" — and Claude fills every invoice field instantly." %}
            </p>
            <div class="flex items-center text-white font-medium group-hover:translate-x-2 transition-transform">
                {% trans "Learn More" %}
                <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
            </div>
        </div>
    </a>

    <!-- Time Tracking Card -->
    <a href="{% url 'feature_time_tracking' %}" class="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-600 to-teal-700 p-8 text-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
        <div class="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
        <div class="absolute bottom-0 left-0 -mb-8 -ml-8 w-40 h-40 bg-cyan-400/20 rounded-full blur-3xl"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-white/20 backdrop-blur-sm">
                    {% trans "NEW" %}
                </span>
            </div>
            <h3 class="text-2xl font-bold mb-3">{% trans "Built-In Time Tracking" %}</h3>
            <p class="text-cyan-100 mb-6">
                {% trans "Start a timer, track your hours, and convert time entries into invoices with one click. No more guessing how long you worked or switching between apps." %}
            </p>
            <div class="flex items-center text-white font-medium group-hover:translate-x-2 transition-transform">
                {% trans "Learn More" %}
                <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
            </div>
        </div>
    </a>
</div>
```

**Step 7: Add a Voice feature card to the features grid**

In the features grid (around line 122), the first card is the AI Invoice Generator (highlighted). Add a Voice card directly after it — before the "Instant PDF Generation" card. Replace the existing plain AI card block and the plain "Instant PDF Generation" card with:

```html
<!-- Feature 1 - AI Invoice Generator -->
<a href="{% url 'feature_ai_invoice_generator' %}" class="p-8 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl border-2 border-purple-200 hover:border-purple-400 transition-all hover:shadow-lg group">
    <div class="flex items-center justify-between mb-6">
        <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
        </div>
        <span class="text-xs font-bold text-purple-600 bg-purple-100 px-2 py-1 rounded">BETA</span>
    </div>
    <h3 class="text-xl font-semibold text-gray-900 mb-3 group-hover:text-purple-700 transition-colors">{% trans "AI Invoice Generator" %}</h3>
    <p class="text-gray-600">{% trans "Describe your work in plain English and let AI create invoice line items instantly. Save hours on data entry." %}</p>
</a>

<!-- Feature - Voice Invoice -->
<a href="{% url 'feature_voice_invoice' %}" class="p-8 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border-2 border-blue-200 hover:border-blue-400 transition-all hover:shadow-lg group">
    <div class="flex items-center justify-between mb-6">
        <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
            </svg>
        </div>
        <span class="text-xs font-bold text-blue-600 bg-blue-100 px-2 py-1 rounded">NEW</span>
    </div>
    <h3 class="text-xl font-semibold text-gray-900 mb-3 group-hover:text-blue-700 transition-colors">{% trans "Voice-to-Invoice" %}</h3>
    <p class="text-gray-600">{% trans "Tap the mic and speak your invoice details. Claude transcribes and fills every field — client, items, rates, and payment terms." %}</p>
</a>

<!-- Feature - Instant PDF -->
<div class="p-8 bg-gray-50 rounded-2xl">
    <div class="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-6">
        <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>
    </div>
    <h3 class="text-xl font-semibold text-gray-900 mb-3">{% trans "Instant PDF Generation" %}</h3>
    <p class="text-gray-600">{% trans "Create professional PDF invoices instantly with your company branding and logo." %}</p>
</div>
```

**Step 8: Verify in browser**

With the dev server still running, open http://127.0.0.1:8000/ and verify:
- Hero H1 reads "With Voice, Text & Time Tracking"
- New Features section has 3 equal-width cards: AI (purple) | Voice (blue) | Time Tracking (cyan)
- Voice card has mic icon and "NEW" badge and links to `/features/voice-invoice/`
- Features grid has a highlighted Voice card with blue border

**Step 9: Commit**

```bash
git add templates/landing/index.html
git commit -m "feat: update landing page to promote voice-to-invoice feature"
```

---

## Task 4: Add cross-links to existing feature pages

**Files:**
- Modify: `templates/features/ai-invoice-generator.html` (Related Features section, lines 644–679)
- Modify: `templates/features/time-tracking.html` (Related Features section, around line 699)

### 4a — AI Invoice Generator page

The Related Features section currently has a single Time Tracking card. Add a Voice card beside it.

Find this section (around line 645):

```html
<!-- Related Features -->
<section class="py-16 bg-white dark:bg-gray-800">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-10">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Pair with Time Tracking for Maximum Efficiency</h2>
            <p class="text-gray-600 dark:text-gray-300">Track hours, then use AI to create the perfect invoice</p>
        </div>

        <a href="{% url 'feature_time_tracking' %}" class="block group">
```

Replace the entire Related Features section with:

```html
<!-- Related Features -->
<section class="py-16 bg-white dark:bg-gray-800">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-10">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Part of the Complete AI Invoicing Suite</h2>
            <p class="text-gray-600 dark:text-gray-300">Combine AI text, voice, and time tracking for the fastest invoicing workflow</p>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
            <!-- Voice Invoice -->
            <a href="{% url 'feature_voice_invoice' %}" class="block group">
                <div class="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl p-6 border-2 border-blue-200 dark:border-blue-800 hover:border-blue-400 dark:hover:border-blue-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                            </svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">Voice-to-Invoice</h3>
                                <span class="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-medium rounded">NEW</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm mb-2">Prefer not to type? Just tap the mic and speak. Claude fills every field from your voice.</p>
                            <span class="inline-flex items-center text-blue-600 dark:text-blue-400 text-sm font-medium group-hover:translate-x-1 transition-transform">
                                Learn about Voice Invoicing
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>

            <!-- Time Tracking -->
            <a href="{% url 'feature_time_tracking' %}" class="block group">
                <div class="bg-gradient-to-br from-cyan-50 to-blue-50 dark:from-cyan-900/20 dark:to-blue-900/20 rounded-2xl p-6 border-2 border-cyan-200 dark:border-cyan-800 hover:border-cyan-400 dark:hover:border-cyan-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-cyan-100 dark:bg-cyan-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-cyan-700 dark:group-hover:text-cyan-400 transition-colors">Time Tracking Invoice Software</h3>
                                <span class="px-2 py-0.5 bg-cyan-100 dark:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300 text-xs font-medium rounded">NEW</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm mb-2">Track billable hours with a live timer. Convert time entries to invoices with one click.</p>
                            <span class="inline-flex items-center text-cyan-600 dark:text-cyan-400 text-sm font-medium group-hover:translate-x-1 transition-transform">
                                Learn about Time Tracking
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>
        </div>
    </div>
</section>
```

### 4b — Time Tracking page

Find the Related Features section (line 699). It currently links only to AI Invoice Generator. Use the same 2-card grid pattern. Replace it with:

```html
<!-- Related Features -->
<section class="py-16 bg-white dark:bg-gray-800">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-10">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Part of the Complete AI Invoicing Suite</h2>
            <p class="text-gray-600 dark:text-gray-300">Combine time tracking, AI text, and voice for the fastest invoicing workflow</p>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
            <!-- AI Invoice Generator -->
            <a href="{% url 'feature_ai_invoice_generator' %}" class="block group">
                <div class="bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-2xl p-6 border-2 border-purple-200 dark:border-purple-800 hover:border-purple-400 dark:hover:border-purple-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                            </svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-purple-700 dark:group-hover:text-purple-400 transition-colors">AI Invoice Generator</h3>
                                <span class="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-xs font-medium rounded">BETA</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm mb-2">Describe your work in plain English and AI creates accurate line items instantly.</p>
                            <span class="inline-flex items-center text-purple-600 dark:text-purple-400 text-sm font-medium group-hover:translate-x-1 transition-transform">
                                Learn about AI Generator
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>

            <!-- Voice Invoice -->
            <a href="{% url 'feature_voice_invoice' %}" class="block group">
                <div class="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl p-6 border-2 border-blue-200 dark:border-blue-800 hover:border-blue-400 dark:hover:border-blue-600 transition-all hover:shadow-lg">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-xl flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
                            </svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-lg font-bold text-gray-900 dark:text-white group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">Voice-to-Invoice</h3>
                                <span class="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-medium rounded">NEW</span>
                            </div>
                            <p class="text-gray-600 dark:text-gray-300 text-sm mb-2">Tap the mic and speak your invoice details. Claude fills every field from your voice.</p>
                            <span class="inline-flex items-center text-blue-600 dark:text-blue-400 text-sm font-medium group-hover:translate-x-1 transition-transform">
                                Learn about Voice Invoicing
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                            </span>
                        </div>
                    </div>
                </div>
            </a>
        </div>
    </div>
</section>
```

**Step: Verify cross-links**

1. Open http://127.0.0.1:8000/features/ai-invoice-generator/ — Related Features should show Voice + Time Tracking cards side by side
2. Open http://127.0.0.1:8000/features/time-tracking/ — Related Features should show AI Generator + Voice cards side by side
3. Click Voice card on both pages — should route to `/features/voice-invoice/`

**Step: Commit**

```bash
git add templates/features/ai-invoice-generator.html templates/features/time-tracking.html
git commit -m "feat: add voice-invoice cross-links to AI and time-tracking feature pages"
```

---

## Task 5: Final verification and push

**Step 1: Full smoke test**

With dev server running, visit these URLs and confirm no errors:
- http://127.0.0.1:8000/ — hero says "With Voice, Text & Time Tracking", 3 highlight cards visible
- http://127.0.0.1:8000/features/voice-invoice/ — full page renders
- http://127.0.0.1:8000/features/ai-invoice-generator/ — Related Features has 2 cards
- http://127.0.0.1:8000/features/time-tracking/ — Related Features has 2 cards
- http://127.0.0.1:8000/sitemap.xml — `/features/voice-invoice/` present in output

**Step 2: Push to Railway**

```bash
git push origin main
```

Railway will auto-deploy. No migrations needed (no model changes).
