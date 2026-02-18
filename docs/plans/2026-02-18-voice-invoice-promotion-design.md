# Voice-to-Invoice Promotion — Design Doc
**Date:** 2026-02-18
**Status:** Approved

## Goal
Promote the Voice-to-Invoice feature across the landing page and SEO, including a new dedicated feature landing page at `/features/voice-invoice/`.

## Scope of Changes

### 1. Landing Page (`templates/landing/index.html`)

**Hero section:**
- Update H1 line 2: "With Built-In Time Tracking" → "With Voice, Text & Time Tracking"
- Update hero description: add voice dictation sentence
- Update meta title to include "voice invoice generator"
- Update meta description to mention voice dictation
- Update meta keywords: add `voice invoice generator, voice to invoice, dictate invoice`

**New Features highlight section:**
- Expand 2-column grid to 3-column grid (md:grid-cols-3)
- Insert new middle card: blue/indigo gradient, mic icon, "NEW" badge, links to `/features/voice-invoice/`
- Copy: "Dictate your invoice by voice. Say 'Built landing page, 8 hours at $120/hr' and Claude fills every field instantly."

**Features grid:**
- Add a highlighted Voice card (similar bordered treatment to AI and Time Tracking cards) with "NEW" badge

### 2. New Feature Page (`templates/features/voice-invoice.html`)

Full SEO landing page mirroring `ai-invoice-generator.html` and `time-tracking.html`:
- Hero: "Invoice by Voice. No Typing Required."
- How it works (3 steps): Tap mic → Speak your work → Apply to invoice
- What gets extracted: client name, email, payment terms, currency, all line items
- JSON-LD schemas: BreadcrumbList, HowTo, FAQPage, SoftwareApplication
- Cross-links section: links to AI Invoice Generator and Time Tracking feature pages
- CTA: links to `/try/` (voice section is available there)
- 4–5 FAQ entries targeting voice invoice search queries

### 3. View + URL + Sitemap

- Add `VoiceInvoiceFeatureView(TemplateView)` to `apps/invoices/views.py`
- Add URL to `config/urls.py`: `path('features/voice-invoice/', VoiceInvoiceFeatureView.as_view(), name='feature_voice_invoice')`
- Add `/features/voice-invoice/` to the sitemap in `config/urls.py`

### 4. Cross-links on Existing Feature Pages

- Add voice to the "Related Features" section on `templates/features/ai-invoice-generator.html`
- Add voice to the "Related Features" section on `templates/features/time-tracking.html`

## Design Decisions

- **Own feature page** chosen over sub-feature treatment — enables targeting "voice invoice generator" keywords independently
- **Hero H1 updated** for maximum prominence (voice joins text AI and time tracking in headline)
- **3-card highlight grid** replaces 2-card grid; voice gets the center/middle card position
- **Blue/indigo gradient** for voice card to distinguish from purple (AI) and cyan (Time Tracking)
- **CTA points to /try/** since the voice UI is already live there with no signup required
