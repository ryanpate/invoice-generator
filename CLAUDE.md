# InvoiceKits - Project Status

## Live Site
**URL:** https://www.invoicekits.com/

**Domain:** www.invoicekits.com (configured)

**Deployment:** Railway with Nixpacks builder

---

## Current Status

### Working Features
- Landing page with pricing display and FAQ section
- User authentication (signup/login/logout via django-allauth)
- User dashboard with invoice stats
- Invoice creation with dynamic line items and optional invoice name
- Invoice editing with pre-populated forms and dynamic totals
- Invoice deletion with confirmation page
- PDF generation with 5 template styles (xhtml2pdf)
- Invoice list with search and status filters (shows invoice name)
- Invoice detail view with status management (shows invoice name)
- Batch CSV upload (for Professional+ plans) with results page
- CSV template download with accurate format guide
- Company profile management with logo upload
- Billing/subscription UI pages
- Account deletion with confirmation and data warning
- REST API endpoints with API key authentication
- API documentation page at `/api/docs/`
- Usage tracking per user
- Admin panel (/admin/) with superuser auto-creation from env vars
- SEO optimizations (meta tags, Open Graph, Twitter Cards, Schema.org, sitemap, robots.txt)
- Stripe subscription payments (Starter $9, Professional $29, Business $79)
- Stripe webhook handling for subscription lifecycle events
- Dark/light mode toggle with browser preference detection and localStorage persistence
- Footer pages: Contact Us, Help Center, Privacy Policy, Terms of Service
- Welcome email on signup (via Resend SMTP)
- Invoice email sending with PDF attachment and customizable message
- Payment receipt emails (auto-sent when invoice marked as paid)
- Social login with Google and GitHub (OAuth fully configured via environment variables)
- Recurring invoices for Professional+ plans (weekly, bi-weekly, monthly, quarterly, yearly)
- Blog section with SEO-optimized content (`/blog/`)

### Suppressed/Disabled Features

| Feature | Status | Reason | To Enable |
|---------|--------|--------|-----------|
| Email Verification | Disabled | Not required for MVP | Change `ACCOUNT_EMAIL_VERIFICATION` to `'mandatory'` in `config/settings/production.py` |
| S3 Media Storage | Disabled | No AWS credentials | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` |
| Healthcheck | Removed | Startup time exceeds Railway timeout | Re-add to `railway.json` if startup is optimized |

---

## Not Yet Implemented (TODOs)

### Critical - Revenue Blocking
- [x] **Stripe Integration:** Configured with live price IDs - COMPLETED
  - Starter: `price_1Smy2w6oOlORkbTyjs4TGG8s` ($9/month)
  - Professional: `price_1Smy3O6oOlORkbTySI4fCIod` ($29/month)
  - Business: `price_1Smy4p6oOlORkbTyXe9hIMKE` ($79/month)
- [x] **Stripe Webhook Handler:** Subscription lifecycle events handled - COMPLETED
- [x] **Watermark on Free Tier PDFs:** Diagonal "FREE PLAN" watermark on all 5 PDF templates - COMPLETED

### High Priority - Core Functionality
- [x] **Invoice Edit Page:** `templates/invoices/edit.html` - COMPLETED
- [x] **Invoice Delete Confirmation:** `templates/invoices/delete_confirm.html` - COMPLETED
- [x] **Batch Result Page:** `templates/invoices/batch_result.html` - COMPLETED
- [x] **Account Delete Confirmation:** `templates/accounts/delete_confirm.html` - COMPLETED
- [x] **Stripe Subscription Cancellation on Account Delete:** COMPLETED
- [x] **Custom Domain Setup:** www.invoicekits.com configured - COMPLETED

### Medium Priority - Growth & Marketing
- [x] **Google Search Console:** Verified and configured
- [x] **Google Analytics:** GA4 tracking code added (G-0NR5NZMNBF)
- [ ] **Google AdSense Integration:** Add to landing page sidebar, dashboard (free users only)
- [x] **Email Notifications:**
  - [x] Welcome email on signup - COMPLETED (via Resend SMTP)
  - [x] Invoice sent notifications - COMPLETED (via Send Invoice feature)
  - [x] Payment receipts - COMPLETED (auto-sends to client + business owner when marked as paid)
- [x] **Social Authentication:** Google and GitHub OAuth fully configured via env vars - COMPLETED
- [x] **Invoice Email Sending:** Send invoices directly to clients via email with PDF attachment - COMPLETED
- [x] **Blog/Content Marketing:** Created `/blog/` section with 4 SEO-optimized posts - COMPLETED

### Lower Priority - Feature Expansion
- [ ] **Team Seats:** Business plan includes 3 team seats (model and UI not implemented)
- [ ] **Enterprise Tier:** Custom pricing, white-label, dedicated support
- [ ] **Premium Templates:** Individual template purchases ($4.99 each)
- [ ] **Affiliate Program:** Referral tracking (20% commission)
- [ ] **QR Code for Payment:** Optional on invoices
- [ ] **Digital Signature Field:** On invoice PDFs
- [x] **Recurring Invoices:** Auto-generate invoices on schedule - COMPLETED (requires Celery/Redis deployment)
- [ ] **Client Portal:** Allow clients to view/pay invoices online
- [ ] **Multi-language Support:** i18n for international users

### SEO - Critical (Week 1)
- [x] **Fix Canonical URL:** Updated `templates/base.html` to use `https://www.invoicekits.com` - COMPLETED
- [x] **Fix Robots.txt Sitemap URL:** Updated `config/urls.py` to use `https://www.invoicekits.com/sitemap.xml` - COMPLETED
- [ ] **Submit Sitemap to GSC:** Submit sitemap.xml via Google Search Console
- [ ] **Request Indexing:** Use GSC URL Inspection tool for all 7 public pages
- [x] **Add Favicon:** Added SVG inline favicon + PNG fallbacks (16x16, 32x32, 180x180) - COMPLETED
- [x] **Add Open Graph Images:** Created og-image.png (1200x630) for social sharing - COMPLETED

### SEO - High Priority (Weeks 2-4)
- [x] **Update Homepage Meta Description:** Expanded to 174 characters with keywords - COMPLETED
- [x] **Update Pricing Page SEO:** Added keyword-rich title, meta description, OG tags - COMPLETED
- [x] **Add Customer Testimonials:** Social proof section on homepage - COMPLETED
- [x] **Create Blog Section:** Launched `/blog/` with Django blog app - COMPLETED
- [x] **Blog Post 1:** "How to Create a Professional Invoice in 2026" - COMPLETED
- [x] **Blog Post 2:** "Batch Invoice Generator: How to Create 100+ Invoices in Minutes" - COMPLETED
- [x] **Blog Post 3:** "Invoice Best Practices for Freelancers: 10 Tips to Get Paid Faster" - COMPLETED
- [x] **Blog Post 4:** "Small Business Invoicing Guide: Templates, Terms, and Tools" - COMPLETED
- [x] **Homepage Template Previews:** Added styled CSS mockups for all 5 templates - COMPLETED
- [ ] **Blog Post 5:** "Invoice vs Receipt: What's the Difference?"
- [ ] **Increase Keyword Density:** Add "invoice generator" 2-3 more times naturally to homepage
- [ ] **Add BreadcrumbList Schema:** Implement breadcrumb navigation and schema on internal pages

### SEO - Content Pages (Month 2)
- [ ] **Template Showcase - Clean Slate:** `/templates/clean-slate/` with screenshots, use cases
- [ ] **Template Showcase - Executive:** `/templates/executive/`
- [ ] **Template Showcase - Bold Modern:** `/templates/bold-modern/`
- [ ] **Template Showcase - Classic Professional:** `/templates/classic-professional/`
- [ ] **Template Showcase - Neon Edge:** `/templates/neon-edge/`
- [ ] **Landing Page - For Freelancers:** `/for-freelancers/` role-specific benefits
- [ ] **Landing Page - For Small Business:** `/for-small-business/`
- [ ] **Landing Page - For Consultants:** `/for-consultants/`
- [ ] **Comparison Page:** "InvoiceKits vs Invoice-Generator.com"
- [ ] **Comparison Page:** "InvoiceKits vs Canva Invoice Maker"

### SEO - Link Building (Month 2-3)
- [ ] **Submit to Product Hunt:** Launch on Product Hunt
- [ ] **Submit to Capterra:** Create business listing
- [ ] **Submit to G2:** Create business listing
- [ ] **Quora Presence:** Answer invoicing questions with links
- [ ] **Reddit Presence:** Engage in r/freelance, r/smallbusiness
- [ ] **Guest Posts:** Reach out to freelancer/entrepreneur blogs
- [ ] **Free Resources:** Create downloadable invoice templates/checklists

### SEO - Advanced (Month 3-6)
- [ ] **FAQ Schema:** Add FAQ structured data to pricing and help pages
- [ ] **Video Tutorials:** Create YouTube content, embed on site
- [ ] **Industry Reports:** "State of Freelance Invoicing 2026"
- [ ] **Free Tools:** Invoice calculator, late fee calculator
- [ ] **Affiliate Program:** Incentivize backlinks
- [ ] **Core Web Vitals:** Run PageSpeed Insights audit, optimize LCP/FID/CLS
- [ ] **Dynamic Sitemap:** Add invoice public links (if public sharing enabled)
- [ ] **International SEO:** Alternate language versions if targeting international markets

### SEO Target Keywords
**High Priority (Unique Opportunity - Low Competition):**
- "batch invoice generator" (720/mo)
- "CSV invoice upload" (590/mo)
- "bulk invoice generation" (480/mo)

**Medium Priority (Informational):**
- "how to create an invoice" (33K/mo)
- "freelance invoice template" (8K/mo)
- "invoice best practices" (1.3K/mo)

**Long-term Targets (High Competition):**
- "free invoice generator" (110K/mo)
- "invoice template" (90K/mo)
- "invoice maker free" (49K/mo)

---

## Environment Variables Required

### Currently Set on Railway
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Railway)
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `ALLOWED_HOSTS` - `.railway.app` added automatically
- `DJANGO_SUPERUSER_EMAIL` - Admin user email
- `DJANGO_SUPERUSER_PASSWORD` - Admin user password
- `STRIPE_LIVE_SECRET_KEY` - Stripe live API key (configured)
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret (configured)
- `EMAIL_HOST` - smtp.resend.com (configured)
- `EMAIL_HOST_USER` - resend (configured)
- `EMAIL_HOST_PASSWORD` - Resend API key (configured)
- `DEFAULT_FROM_EMAIL` - InvoiceKits <noreply@invoicekits.com> (configured)
- `SITE_URL` - https://www.invoicekits.com (configured)
- `DOMAIN` - invoicekits.com (configured)
- `GOOGLE_OAUTH_CLIENT_ID` - Google OAuth client ID (configured)
- `GOOGLE_OAUTH_CLIENT_SECRET` - Google OAuth client secret (configured)
- `GITHUB_OAUTH_CLIENT_ID` - GitHub OAuth client ID (configured)
- `GITHUB_OAUTH_CLIENT_SECRET` - GitHub OAuth client secret (configured)

### Optional - Not Yet Configured
```bash
# AWS S3 (for media file storage - logos currently stored locally)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...

# Redis (for Celery async tasks - not needed for current functionality)
REDIS_URL=redis://...
```

---

## Project Structure

```
invoice_generator/
├── config/
│   ├── settings/
│   │   ├── base.py          # Core settings, subscription tiers
│   │   ├── development.py   # Local dev
│   │   └── production.py    # Railway production
│   ├── urls.py              # Main URLs + sitemap + robots.txt
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/            # User model, dashboard, settings
│   ├── billing/             # Subscription & Stripe
│   ├── invoices/            # Invoice CRUD, PDF generation
│   │   └── services/
│   │       ├── pdf_generator.py   # xhtml2pdf PDF generation
│   │       ├── batch_processor.py # CSV batch processing
│   │       └── email_sender.py    # Invoice email sending with PDF
│   ├── companies/           # Company profiles & branding
│   ├── api/                 # REST API (DRF)
│   └── blog/                # SEO blog content
│       ├── models.py        # BlogPost, BlogCategory
│       ├── views.py         # List, Detail, Category views
│       ├── urls.py          # Blog URL routing
│       ├── sitemaps.py      # Blog sitemap for SEO
│       └── management/commands/seed_blog.py  # Blog post seeder
├── templates/
│   ├── account/             # allauth templates (login, signup)
│   ├── blog/                # Blog templates (list, detail)
│   ├── dashboard/
│   ├── emails/              # Email templates (welcome, recurring, etc.)
│   ├── invoices/
│   │   ├── pdf/             # 5 PDF templates
│   │   └── recurring/       # Recurring invoice templates (list, detail, create, edit, delete)
│   ├── billing/
│   ├── landing/             # Home page with FAQ + pricing
│   ├── pages/               # Static pages (contact, help, privacy, terms, api_docs)
│   └── settings/
├── static/
│   └── robots.txt           # Search engine instructions
├── nixpacks.toml            # Railway build config
└── railway.json             # Railway deploy config with startCommand
```

---

## Key Files

| File | Purpose |
|------|---------|
| `config/settings/base.py` | Subscription tiers, invoice templates, core config |
| `config/settings/production.py` | Railway-specific settings, security, CSRF, email config |
| `config/urls.py` | Main URL routing + sitemap + robots.txt views |
| `apps/accounts/models.py` | CustomUser with subscription tracking |
| `apps/accounts/signals.py` | Welcome email signal handler (user_signed_up) |
| `apps/invoices/models.py` | Invoice model with invoice_name field |
| `apps/invoices/forms.py` | InvoiceForm with invoice_name field |
| `apps/invoices/services/pdf_generator.py` | xhtml2pdf PDF generation with watermark |
| `apps/invoices/services/email_sender.py` | Invoice email & payment receipt sending |
| `apps/invoices/signals.py` | Payment receipt signal handler (post_save) |
| `apps/billing/views.py` | Stripe checkout flow with live price IDs |
| `apps/api/views.py` | REST API endpoints |
| `apps/invoices/tasks.py` | Celery tasks for recurring invoice processing |
| `templates/base.html` | Base template with SEO meta tags + Schema.org + GA4 |
| `templates/emails/welcome.html` | HTML welcome email template |
| `templates/emails/payment_receipt.html` | Payment receipt email template |
| `templates/emails/recurring_invoice_generated.html` | Recurring invoice notification email |
| `templates/emails/invoice_to_client.html` | Invoice email sent to clients |
| `templates/landing/index.html` | Landing page with FAQ + FAQPage schema |
| `templates/landing/pricing.html` | Pricing page with SEO meta tags |
| `templates/blog/list.html` | Blog listing page with search/filter |
| `templates/blog/detail.html` | Blog post detail with Schema.org BlogPosting |
| `apps/blog/models.py` | BlogPost, BlogCategory models |
| `apps/blog/sitemaps.py` | BlogPostSitemap for SEO |
| `apps/blog/management/commands/seed_blog.py` | Seeds blog posts on deploy |
| `railway.json` | Railway deploy config with startCommand |
| `nixpacks.toml` | Nix packages for build |

---

## Subscription Tiers

| Tier | Price | Invoices/mo | Features |
|------|-------|-------------|----------|
| Free | $0 | 5 | 1 template, watermark |
| Starter | $9 | 50 | 2 templates, no watermark |
| Professional | $29 | 200 | All templates, batch upload, recurring invoices (up to 10) |
| Business | $79 | Unlimited | API access (1000 calls/mo), unlimited recurring invoices |

---

## SEO Implementation

### Technical SEO (Completed)
- **Meta Tags:** Title, description, keywords, canonical URL, robots meta
- **Open Graph:** og:type, og:url, og:title, og:description, og:site_name
- **Twitter Cards:** twitter:card, twitter:title, twitter:description
- **Schema.org Markup:**
  - SoftwareApplication schema on all pages (`templates/base.html`)
  - FAQPage schema on landing page (`templates/landing/index.html`)
- **Sitemap:** XML sitemap at `/sitemap.xml` (includes all public pages)
- **Robots.txt:** Available at `/robots.txt` with proper allow/disallow rules
- **FAQ Section:** 6 keyword-rich Q&As on landing page

### SEO URLs
| URL | Purpose |
|-----|---------|
| `/sitemap.xml` | XML sitemap for search engines |
| `/robots.txt` | Search engine crawler instructions |
| `/#faq` | FAQ section with structured data |
| `/contact/` | Contact Us page with support email |
| `/help/` | Help Center with FAQs |
| `/privacy/` | Privacy Policy |
| `/terms/` | Terms of Service |
| `/api/docs/` | API documentation |
| `/blog/` | Blog listing page |
| `/blog/<slug>/` | Individual blog post |
| `/blog/category/<slug>/` | Posts by category |

### Blog Posts (Live)
| URL | Title | Target Keyword |
|-----|-------|----------------|
| `/blog/how-to-create-professional-invoice/` | How to Create a Professional Invoice in 2026 | "how to create an invoice" (33K/mo) |
| `/blog/batch-invoice-generator-guide/` | Batch Invoice Generator: How to Create 100+ Invoices | "batch invoice generator" (720/mo) |
| `/blog/freelancer-invoice-tips-get-paid-faster/` | Invoice Best Practices for Freelancers | "freelance invoice template" (8K/mo) |
| `/blog/small-business-invoicing-guide/` | Small Business Invoicing Guide | "small business invoice" |

### Recurring Invoice URLs (Professional+ only)
| URL | Purpose |
|-----|---------|
| `/invoices/recurring/` | List all recurring invoices |
| `/invoices/recurring/create/` | Create new recurring invoice |
| `/invoices/recurring/<pk>/` | View recurring invoice details |
| `/invoices/recurring/<pk>/edit/` | Edit recurring invoice |
| `/invoices/recurring/<pk>/delete/` | Delete confirmation |
| `/invoices/recurring/<pk>/toggle-status/` | Pause/Resume recurring |
| `/invoices/recurring/<pk>/generate-now/` | Manual invoice generation |

### Meta Tags Override (for child templates)
```html
{% block meta_description %}Custom description{% endblock %}
{% block meta_keywords %}custom, keywords{% endblock %}
{% block canonical_url %}https://invoicekits.com/page{% endblock %}
{% block og_title %}Custom OG Title{% endblock %}
{% block og_description %}Custom OG description{% endblock %}
{% block twitter_title %}Custom Twitter title{% endblock %}
{% block twitter_description %}Custom Twitter description{% endblock %}
{% block extra_schema %}Additional JSON-LD{% endblock %}
```

### SEO TODOs
- [x] Register with Google Search Console
- [x] Add Google Analytics tracking (G-0NR5NZMNBF)
- [x] Create blog content for keyword targeting (4 posts live)
- [x] Set up custom domain (www.invoicekits.com)
- [ ] Submit sitemap to Google Search Console
- [ ] Request indexing for all public pages via GSC URL Inspection
- [ ] Build quality backlinks (Product Hunt, directories)
- [ ] Monitor Core Web Vitals via PageSpeed Insights

---

## Invoice Templates

| Template | Style | Best For |
|----------|-------|----------|
| Clean Slate | Minimalist white, modern sans-serif | Tech companies, startups |
| Executive | Navy & gold accents, serif headings | Consulting, legal, finance |
| Bold Modern | Vibrant colors, large typography | Creative agencies, designers |
| Classic Professional | Traditional layout, subtle grays | General business, accounting |
| Neon Edge | Dark mode, neon accents | Gaming, tech, entertainment |

All templates support:
- Company logo display
- Invoice name field
- Multi-currency formatting
- Tax calculations
- Notes section
- "FREE PLAN" watermark (for free tier users)

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/invoices/` | GET, POST | List/create invoices |
| `/api/v1/invoices/{id}/` | GET, PUT, DELETE | Invoice detail/update/delete |
| `/api/v1/invoices/{id}/pdf/` | GET | Download PDF |
| `/api/v1/companies/` | GET, PUT | Company profile |
| `/api/v1/usage/` | GET | API usage stats |

Authentication: API Key in header `X-API-Key: <key>`

---

## Recent Fixes (Deployment History)

1. Fixed ALLOWED_HOSTS to include `.railway.app`
2. Removed placeholder Stripe keys causing djstripe crash
3. Switched from Ubuntu apt packages to Nix packages for WeasyPrint dependencies
4. Removed healthcheck (startup exceeds timeout)
5. Fixed template URL namespaces (`landing:index` -> `invoices:landing`)
6. Fixed allauth URL names (`accounts:login` -> `account_login`)
7. Disabled email verification (SMTP not configured)
8. Rebranded from "Invoice Pro" to "InvoiceKits"
9. Fixed CSRF trusted origins for `*.up.railway.app`
10. Added superuser auto-creation from env vars in `railway.json` startCommand
11. Switched from WeasyPrint to xhtml2pdf (pure Python, no system library dependencies)
12. Added `invoice_name` field to Invoice model for naming invoices
13. Invoice name displays on list page, detail page, and all 5 PDF templates
14. Added SEO enhancements: meta tags, Open Graph, Twitter Cards, Schema.org markup
15. Added XML sitemap (`/sitemap.xml`) and robots.txt (`/robots.txt`)
16. Added FAQ section to landing page with FAQPage structured data
17. Added `django.contrib.sitemaps` to INSTALLED_APPS
18. Fixed batch upload CSV template download button (was broken link)
19. Updated CSV Format Guide to match actual batch processor requirements
20. Created Invoice Edit page template with dynamic total calculation
21. Created Invoice Delete Confirmation template
22. Created Batch Result page template with status display and ZIP download
23. Created Account Delete Confirmation template with data deletion warnings
24. Added prominent "FREE PLAN" diagonal watermark to all 5 PDF templates for free tier users
25. Fixed watermark CSS for xhtml2pdf compatibility (position:absolute instead of position:fixed)
26. Configured Stripe live price IDs for all subscription tiers
27. Added dark/light mode toggle with browser preference detection and localStorage persistence
28. Fixed settings pages that were stuck in dark mode only
29. Added responsive dark/light mode to all application pages (dashboard, invoices, batch upload, etc.)
30. Created footer pages: Contact Us, Help Center, Privacy Policy, Terms of Service
31. Created comprehensive API documentation page at `/api/docs/`
32. Fixed Features footer link to properly navigate to landing page #features section
33. Added all new pages to sitemap and robots.txt
34. Added Google Analytics GA4 tracking (G-0NR5NZMNBF)
35. Added welcome email on signup (signal handler + HTML email template)
36. Configured Resend SMTP for email delivery (EMAIL_HOST=smtp.resend.com)
37. Fixed Railway environment variable with leading space in key name
38. Added invoice email sending feature with PDF attachment and customizable message
39. Created InvoiceEmailService in `apps/invoices/services/email_sender.py`
40. Created invoice notification email template `templates/emails/invoice_notification.html`
41. Added Send Email button to invoice detail and list pages
42. Added automatic payment receipt emails when invoice marked as paid
43. Created payment receipt email template `templates/emails/payment_receipt.html`
44. Added signals handler `apps/invoices/signals.py` for payment notifications
45. Configured Google and GitHub social login with django-allauth
46. Added SOCIALACCOUNT_PROVIDERS settings for Google and GitHub OAuth
47. Updated login and signup templates with provider login URLs
48. Created data migration to configure OAuth apps from environment variables
49. Fixed OAuth migration timing issue with ensure_oauth_apps migration
50. Added recurring invoices feature for Professional+ plans
51. Created RecurringInvoice and RecurringLineItem models with scheduling logic
52. Added django-celery-beat for periodic task scheduling
53. Created Celery tasks for processing recurring invoices (daily at 6 AM UTC)
54. Added recurring invoice CRUD views with subscription tier checks
55. Created recurring invoice templates (list, detail, create, edit, delete)
56. Created recurring invoice notification emails (owner notification, client invoice)
57. Added RecurringInvoiceAdmin with bulk pause/resume actions
58. Updated subscription tiers with recurring invoice limits (Pro: 10, Business: unlimited)
59. Deployed Redis service on Railway for Celery message broker
60. Created and deployed celery-worker service for async task processing
61. Created and deployed celery-beat service for periodic task scheduling
62. Configured REDIS_URL environment variable for all services
63. Recurring invoice auto-generation now fully operational
64. Updated Pricing page with SEO title, meta description, Open Graph tags
65. Added customer testimonials section to homepage
66. Created Django blog app with BlogPost and BlogCategory models
67. Added blog templates (list.html, detail.html) with full SEO support
68. Created BlogPostSitemap for automatic sitemap inclusion
69. Added seed_blog management command for automated blog seeding on deploy
70. Blog Post 1: "How to Create a Professional Invoice in 2026"
71. Blog Post 2: "Batch Invoice Generator Guide"
72. Blog Post 3: "Invoice Best Practices for Freelancers"
73. Blog Post 4: "Small Business Invoicing Guide"
74. Added Blog link to footer navigation
75. Fixed homepage template previews with styled CSS mockups
76. Added internal cross-linking between blog posts

---

## Development Commands

```bash
# Local development
source .venv/bin/activate
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser locally
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test
```

---

## Deployment Notes

### Railway Configuration
- **Builder:** Nixpacks
- **Start Command:** Defined in `railway.json` (runs migrations + superuser creation + gunicorn)
- **Database:** PostgreSQL (auto-provisioned)
- **Static Files:** Served via WhiteNoise

### Production Checklist (All Complete)
- [x] Set all environment variables
- [x] Configure Stripe products and price IDs
- [x] Set up custom domain DNS (www.invoicekits.com)
- [x] Enable HTTPS (automatic on Railway)
- [x] Configure email delivery (Resend SMTP)
- [x] Set up Google Analytics (G-0NR5NZMNBF)
- [x] Register with Google Search Console
- [x] Configure Google and GitHub OAuth social login
- [x] Add Redis service on Railway (for recurring invoices)
- [x] Deploy Celery worker service
- [x] Deploy Celery Beat service

### Celery Infrastructure (Deployed)
The following services are deployed on Railway for recurring invoice auto-generation:

| Service | Purpose | Status |
|---------|---------|--------|
| Redis | Message broker for Celery | Running |
| celery-worker | Processes async tasks | Running |
| celery-beat | Schedules periodic tasks | Running |

**Schedule:** Recurring invoices process daily at 6:00 AM UTC.

**Internal URLs:**
- Redis: `redis://Redis.railway.internal:6379`
- All services share the same `DATABASE_URL` and `REDIS_URL`
