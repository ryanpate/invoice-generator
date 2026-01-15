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
- Blog section with SEO-optimized content (`/blog/`) - 5 posts live
- Role-specific landing pages (`/for-freelancers/`, `/for-small-business/`, `/for-consultants/`)
- Competitor comparison page (`/compare/`)
- Template showcase pages (`/templates/clean-slate/`, `/templates/executive/`, `/templates/bold-modern/`, `/templates/classic-professional/`, `/templates/neon-edge/`)
- QR code on invoice PDFs linking to public invoice view page (available to all users)
- Digital signature on invoice PDFs (upload in Company Settings, appears on all invoice templates)
- **Hybrid Credits + Subscriptions billing model:**
  - Credit system for pay-as-you-go users (5 free lifetime credits on signup)
  - Credit packs: 10 credits ($9), 25 credits ($19), 50 credits ($35)
  - Subscriptions for regular users (better per-invoice value)
  - Credits never expire, no watermark after purchase
  - Dashboard shows credits for credit users, usage % for subscribers
- **Team Seats for Business plan:**
  - Up to 3 team members per company
  - Roles: Admin (full access) and Member (create/view invoices)
  - Team management at `/settings/team/`
  - Email invitations with secure token-based acceptance
  - Team members share company invoices and settings
- **Client Portal for invoice recipients:**
  - Magic link authentication (no passwords needed)
  - Client dashboard at `/portal/` with invoice overview
  - View all invoices from all businesses in one place
  - Online payments via Stripe Connect (paid directly to business)
  - Payment history and downloadable PDF statements
  - Businesses connect Stripe at `/billing/stripe-connect/`
- **Premium Templates (one-time purchases):**
  - 2 Free templates: Clean Slate, Classic Professional
  - 3 Premium templates ($4.99 each): Executive, Bold Modern, Neon Edge
  - Bundle option ($9.99): All 3 premium templates (~33% discount)
  - Template store at `/billing/templates/`
  - Purchased templates persist indefinitely
  - Subscription tiers (Pro/Business) include all templates automatically
- **Free SEO Tools (no login required):**
  - Invoice Calculator (`/tools/invoice-calculator/`) - Line items mode & hourly rate mode, tax/discount, live totals
  - Late Fee Calculator (`/tools/late-fee-calculator/`) - Flat fee, percentage, compound interest, payment terms presets
- **Multi-Language Support (i18n):**
  - Languages: English (default), Spanish (es), French (fr)
  - URL strategy: `/es/pricing/`, `/fr/pricing/`, `/pricing/` (English - no prefix)
  - Scope: Public pages only (landing, pricing, templates, tools, blog, footer pages)
  - Authenticated routes (dashboard, invoices, billing) remain English-only
  - Language switcher dropdown in navigation
  - hreflang tags for SEO
  - ~1,077 translatable strings per language
  - Translation files: `locale/es/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.po`
- **Affiliate Program (20% commission):**
  - Referral tracking via cookies (30-day duration)
  - Commission on all purchases (subscriptions, credit packs, templates)
  - Affiliate dashboard at `/affiliate/` with stats and referral links
  - Application workflow with admin approval
  - Public program landing page at `/affiliate/program/`
  - Referral links: `/ref/<code>/`

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
- [x] **Hybrid Credits + Subscriptions Model:** Code implemented - COMPLETED
- [x] **Stripe Credit Pack Products:** Created in Stripe Dashboard - COMPLETED
  - 10 Credit Pack ($9): `price_1SnqlJ6oOlORkbTyjaW6sjR4`
  - 25 Credit Pack ($19): `price_1Snqlh6oOlORkbTyeaL4R5dQ`
  - 50 Credit Pack ($35): `price_1Snqm46oOlORkbTycROhS9fV`

### High Priority - Core Functionality
- [x] **Invoice Edit Page:** `templates/invoices/edit.html` - COMPLETED
- [x] **Invoice Delete Confirmation:** `templates/invoices/delete_confirm.html` - COMPLETED
- [x] **Batch Result Page:** `templates/invoices/batch_result.html` - COMPLETED
- [x] **Account Delete Confirmation:** `templates/accounts/delete_confirm.html` - COMPLETED
- [x] **Stripe Subscription Cancellation on Account Delete:** COMPLETED
- [x] **Custom Domain Setup:** www.invoicekits.com configured - COMPLETED

### Medium Priority - Growth & Marketing
- [x] **Google Search Console:** Verified and configured
- [x] **Bing Webmaster Tools:** Verified and configured (BingSiteAuth.xml served at `/BingSiteAuth.xml`)
- [x] **Google Analytics:** GA4 tracking code added (G-0NR5NZMNBF)
- [ ] **Google AdSense Integration:** Add to landing page sidebar, dashboard (free users only)
- [x] **Email Notifications:**
  - [x] Welcome email on signup - COMPLETED (via Resend SMTP)
  - [x] Invoice sent notifications - COMPLETED (via Send Invoice feature)
  - [x] Payment receipts - COMPLETED (auto-sends to client + business owner when marked as paid)
- [x] **Social Authentication:** Google and GitHub OAuth fully configured via env vars - COMPLETED
- [x] **Invoice Email Sending:** Send invoices directly to clients via email with PDF attachment - COMPLETED
- [x] **Blog/Content Marketing:** Created `/blog/` section with 5 SEO-optimized posts - COMPLETED

### Lower Priority - Feature Expansion
- [x] **Team Seats:** Business plan includes 3 team seats - COMPLETED
  - Team members can create/view invoices for the same company
  - Roles: Admin (manage team + settings) and Member (create/view invoices)
  - Team management at `/settings/team/`
  - Email invitations with 7-day expiration
  - Auto-accept invitations on signup/login
- [ ] **Enterprise Tier:** Custom pricing, white-label, dedicated support
- [x] **Premium Templates:** Individual template purchases ($4.99 each) - COMPLETED
  - Free templates: Clean Slate, Classic Professional
  - Premium templates ($4.99 each): Executive, Bold Modern, Neon Edge
  - Bundle ($9.99): All 3 premium templates
  - Template store at `/billing/templates/`
- [x] **Affiliate Program:** Referral tracking (20% commission) - COMPLETED
- [x] **QR Code on Invoice PDFs:** Links to public invoice page for viewing and marking as paid - COMPLETED
- [x] **Digital Signature Field:** On invoice PDFs - COMPLETED (upload in Company Settings, displays on all templates)
- [x] **Recurring Invoices:** Auto-generate invoices on schedule - COMPLETED (requires Celery/Redis deployment)
- [x] **Client Portal:** Allow clients to view/pay invoices online - COMPLETED
  - Magic link authentication (passwordless, 30-min expiry, rate-limited)
  - Client dashboard with invoice overview and payment history
  - Stripe Connect for direct payments to businesses
  - Invoice list with search, status, and company filters
  - Online payment via Stripe Checkout with transfer to business
  - Downloadable PDF statements
  - Available at `/portal/`
- [x] **Multi-language Support:** i18n for international users (Spanish, French) - COMPLETED

### SEO - Critical (Week 1)
- [x] **Fix Canonical URL:** Updated `templates/base.html` to use `https://www.invoicekits.com` - COMPLETED
- [x] **Fix Robots.txt Sitemap URL:** Updated `config/urls.py` to use `https://www.invoicekits.com/sitemap.xml` - COMPLETED
- [x] **Submit Sitemap to GSC:** Submit sitemap.xml via Google Search Console - COMPLETED
- [x] **Request Indexing:** Use GSC URL Inspection tool for all 7 public pages - COMPLETED
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
- [x] **Blog Post 5:** "Invoice vs Receipt: What's the Difference?" - COMPLETED
- [x] **Increase Keyword Density:** Added "invoice generator" 4 more times naturally to homepage - COMPLETED
- [x] **Add BreadcrumbList Schema:** Implement breadcrumb navigation and schema on internal pages - COMPLETED

### SEO - Content Pages (Month 2)
- [x] **Template Showcase - Clean Slate:** `/templates/clean-slate/` with screenshots, use cases - COMPLETED
- [x] **Template Showcase - Executive:** `/templates/executive/` - COMPLETED
- [x] **Template Showcase - Bold Modern:** `/templates/bold-modern/` - COMPLETED
- [x] **Template Showcase - Classic Professional:** `/templates/classic-professional/` - COMPLETED
- [x] **Template Showcase - Neon Edge:** `/templates/neon-edge/` - COMPLETED
- [x] **Landing Page - For Freelancers:** `/for-freelancers/` role-specific benefits - COMPLETED
- [x] **Landing Page - For Small Business:** `/for-small-business/` - COMPLETED
- [x] **Landing Page - For Consultants:** `/for-consultants/` - COMPLETED
- [x] **Comparison Page:** `/compare/` - Comprehensive comparison vs Invoice-Generator.com, Canva, Wave, Zoho - COMPLETED

### SEO - Link Building (Month 2-3)
- [ ] **Submit to Product Hunt:** Launch on Product Hunt
- [ ] **Submit to Capterra:** Create business listing
- [ ] **Submit to G2:** Create business listing
- [ ] **Quora Presence:** Answer invoicing questions with links
- [ ] **Reddit Presence:** Engage in r/freelance, r/smallbusiness
- [ ] **Guest Posts:** Reach out to freelancer/entrepreneur blogs
- [ ] **Free Resources:** Create downloadable invoice templates/checklists

### SEO - Advanced (Month 3-6)
- [x] **FAQ Schema:** Add FAQ structured data to pricing and help pages - COMPLETED
- [ ] **Video Tutorials:** Create YouTube content, embed on site
- [ ] **Industry Reports:** "State of Freelance Invoicing 2026"
- [x] **Free Tools:** Invoice calculator, late fee calculator - COMPLETED
- [x] **Affiliate Program:** Incentivize backlinks - COMPLETED
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

### Stripe Credit Pack Products (Configured)
```bash
STRIPE_CREDIT_PACK_10_PRICE_ID=price_1SnqlJ6oOlORkbTyjaW6sjR4  # 10 credits for $9
STRIPE_CREDIT_PACK_25_PRICE_ID=price_1Snqlh6oOlORkbTyeaL4R5dQ  # 25 credits for $19
STRIPE_CREDIT_PACK_50_PRICE_ID=price_1Snqm46oOlORkbTycROhS9fV  # 50 credits for $35
```

### Stripe Premium Template Products (Configured)
```bash
STRIPE_TEMPLATE_EXECUTIVE_PRICE_ID=price_1SpaNc6oOlORkbTyfrk17jmF   # Executive template $4.99
STRIPE_TEMPLATE_BOLD_MODERN_PRICE_ID=price_1SpaNv6oOlORkbTy5xexCHJu # Bold Modern template $4.99
STRIPE_TEMPLATE_NEON_EDGE_PRICE_ID=price_1SpaOI6oOlORkbTyeb97MXDr   # Neon Edge template $4.99
STRIPE_TEMPLATE_BUNDLE_PRICE_ID=price_1SpaOp6oOlORkbTyBr8HcACD      # All templates bundle $9.99
```

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
│   ├── showcase/            # Template showcase pages (clean-slate, executive, bold-modern, classic-professional, neon-edge)
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
| `config/settings/base.py` | Subscription tiers, credit packs, invoice templates, core config |
| `config/settings/production.py` | Railway-specific settings, security, CSRF, email config |
| `config/urls.py` | Main URL routing + sitemap + robots.txt views |
| `apps/accounts/models.py` | CustomUser with subscription tracking + credit system |
| `apps/accounts/signals.py` | Welcome email signal handler (user_signed_up) |
| `apps/invoices/models.py` | Invoice model with invoice_name field |
| `apps/invoices/forms.py` | InvoiceForm with invoice_name field |
| `apps/invoices/services/pdf_generator.py` | xhtml2pdf PDF generation with watermark + QR code |
| `templates/invoices/public_view.html` | Public invoice view page (for QR code links) |
| `apps/invoices/services/email_sender.py` | Invoice email & payment receipt sending |
| `apps/invoices/signals.py` | Payment receipt signal handler (post_save) |
| `apps/billing/models.py` | CreditPurchase, TemplatePurchase models for one-time purchases |
| `apps/billing/views.py` | Stripe checkout for subscriptions, credits, and template purchases |
| `templates/billing/templates.html` | Premium template store page |
| `templates/billing/templates_success.html` | Template purchase success page |
| `apps/api/views.py` | REST API endpoints |
| `apps/invoices/tasks.py` | Celery tasks for recurring invoice processing |
| `templates/base.html` | Base template with SEO meta tags + Schema.org + GA4 |
| `templates/emails/welcome.html` | HTML welcome email template |
| `templates/emails/payment_receipt.html` | Payment receipt email template |
| `templates/emails/recurring_invoice_generated.html` | Recurring invoice notification email |
| `templates/emails/invoice_to_client.html` | Invoice email sent to clients |
| `templates/landing/index.html` | Landing page with FAQ + FAQPage schema |
| `templates/landing/pricing.html` | Pricing page with SEO meta tags |
| `templates/billing/credits.html` | Credit pack purchase page |
| `templates/billing/credits_success.html` | Credit purchase success page |
| `templates/billing/overview.html` | Billing overview (credits + subscription) |
| `templates/billing/plans.html` | Subscription plans + pay-as-you-go section |
| `templates/blog/list.html` | Blog listing page with search/filter |
| `templates/blog/detail.html` | Blog post detail with Schema.org BlogPosting |
| `apps/blog/models.py` | BlogPost, BlogCategory models |
| `apps/blog/sitemaps.py` | BlogPostSitemap for SEO |
| `apps/blog/management/commands/seed_blog.py` | Seeds blog posts on deploy |
| `railway.json` | Railway deploy config with startCommand |
| `nixpacks.toml` | Nix packages for build |
| `templates/showcase/clean-slate.html` | Clean Slate template showcase page |
| `templates/showcase/executive.html` | Executive template showcase page |
| `templates/showcase/bold-modern.html` | Bold Modern template showcase page |
| `templates/showcase/classic-professional.html` | Classic Professional template showcase page |
| `templates/showcase/neon-edge.html` | Neon Edge template showcase page |
| `apps/companies/models.py` | Company, TeamMember, TeamInvitation models |
| `apps/companies/views.py` | Team management views (invite, accept, remove) |
| `apps/companies/signals.py` | Auto-accept invitations on signup/login |
| `apps/companies/services/team_email.py` | Team invitation and welcome emails |
| `templates/settings/team.html` | Team management UI page |
| `templates/emails/team_invitation.html` | Team invitation email template |
| `templates/emails/team_welcome.html` | Team welcome email template |
| `apps/clients/models.py` | Client, MagicLinkToken, ClientSession, ClientPayment models |
| `apps/clients/views.py` | Client portal views (dashboard, invoices, payments) |
| `apps/clients/services/magic_link.py` | Magic link authentication service |
| `apps/billing/services/stripe_connect.py` | Stripe Connect service for business payments |
| `templates/clients/base_portal.html` | Client portal base template |
| `templates/clients/dashboard.html` | Client portal dashboard |
| `templates/clients/invoice_detail.html` | Client invoice view with pay button |
| `templates/emails/client_magic_link.html` | Magic link email template |
| `templates/billing/stripe_connect_status.html` | Stripe Connect management page |
| `apps/affiliates/models.py` | Affiliate, Referral, Commission, AffiliateApplication models |
| `apps/affiliates/views.py` | Affiliate dashboard, apply, referral redirect views |
| `apps/affiliates/signals.py` | Connect referral cookies to new user signups |
| `apps/affiliates/services/commission_tracker.py` | Commission creation service (20% rate) |
| `templates/affiliates/dashboard.html` | Affiliate dashboard with stats and referral links |
| `templates/affiliates/program.html` | Public affiliate program landing page |

---

## Pricing Model (Hybrid Credits + Subscriptions)

### Credit Packs (Pay-as-you-go)
| Pack | Price | Credits | Per-Invoice | Features |
|------|-------|---------|-------------|----------|
| Free | $0 | 5 (lifetime) | — | 1 template, watermark |
| 10 Credits | $9 | 10 | $0.90 | All templates, no watermark |
| 25 Credits | $19 | 25 | $0.76 | All templates, no watermark |
| 50 Credits | $35 | 50 | $0.70 | All templates, no watermark |

### Subscriptions (Monthly)
| Tier | Price | Invoices/mo | Per-Invoice | Features |
|------|-------|-------------|-------------|----------|
| Starter | $9/mo | 50 | $0.18 | All templates, no watermark |
| Professional | $29/mo | 200 | $0.15 | + Batch upload, recurring invoices (up to 10) |
| Business | $79/mo | Unlimited | — | + API access (1000 calls/mo), unlimited recurring, 3 team seats |

**Notes:**
- Credits never expire
- New users get 5 free lifetime credits
- Watermark removed after any credit purchase
- Subscriptions offer better per-invoice value for regular users

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
| `/for-freelancers/` | Landing page for freelancers |
| `/for-small-business/` | Landing page for small businesses |
| `/for-consultants/` | Landing page for consultants |
| `/compare/` | Competitor comparison page |
| `/blog/` | Blog listing page |
| `/blog/<slug>/` | Individual blog post |
| `/blog/category/<slug>/` | Posts by category |
| `/templates/clean-slate/` | Clean Slate template showcase |
| `/templates/executive/` | Executive template showcase |
| `/templates/bold-modern/` | Bold Modern template showcase |
| `/templates/classic-professional/` | Classic Professional template showcase |
| `/templates/neon-edge/` | Neon Edge template showcase |
| `/tools/invoice-calculator/` | Free invoice calculator tool |
| `/tools/late-fee-calculator/` | Free late fee calculator tool |

### Team Management URLs (Business Tier Only)
| URL | Purpose |
|-----|---------|
| `/settings/team/` | Team management page |
| `/settings/team/invite/` | Send team invitation (POST) |
| `/settings/team/member/<pk>/remove/` | Remove team member (POST) |
| `/settings/team/invitation/<pk>/cancel/` | Cancel invitation (POST) |
| `/invitation/<uuid>/` | Accept team invitation (public) |

### Public Invoice URLs (No Auth Required)
| URL | Purpose |
|-----|---------|
| `/invoice/<uuid>/` | Public invoice view (from QR code) |
| `/invoice/<uuid>/mark-paid/` | Mark invoice as paid (POST) |
| `/invoice/<uuid>/pdf/` | Download PDF from public view |

### Blog Posts (Live)
| URL | Title | Target Keyword |
|-----|-------|----------------|
| `/blog/how-to-create-professional-invoice/` | How to Create a Professional Invoice in 2026 | "how to create an invoice" (33K/mo) |
| `/blog/batch-invoice-generator-guide/` | Batch Invoice Generator: How to Create 100+ Invoices | "batch invoice generator" (720/mo) |
| `/blog/freelancer-invoice-tips-get-paid-faster/` | Invoice Best Practices for Freelancers | "freelance invoice template" (8K/mo) |
| `/blog/small-business-invoicing-guide/` | Small Business Invoicing Guide | "small business invoice" |
| `/blog/invoice-vs-receipt-difference/` | Invoice vs Receipt: What's the Difference? | "invoice vs receipt" |

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

### Credit System URLs
| URL | Purpose |
|-----|---------|
| `/billing/credits/` | View credit balance and purchase credit packs |
| `/billing/credits/purchase/<pack_id>/` | Initiate credit pack purchase |
| `/billing/credits/success/` | Credit purchase success page |

### Premium Template Store URLs
| URL | Purpose |
|-----|---------|
| `/billing/templates/` | Premium template store page |
| `/billing/templates/purchase/<template_id>/` | Initiate template purchase |
| `/billing/templates/success/` | Template purchase success page |

### Affiliate Program URLs
| URL | Purpose |
|-----|---------|
| `/affiliate/` | Affiliate dashboard (approved affiliates only) |
| `/affiliate/apply/` | Apply to become an affiliate |
| `/affiliate/program/` | Public affiliate program landing page |
| `/affiliate/commissions/` | View all commission history |
| `/affiliate/referrals/` | View all referral history |
| `/ref/<code>/` | Referral redirect link (sets 30-day cookie) |

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

### URLs Pending Google Search Console Indexing
The following pages need to be submitted for indexing via GSC URL Inspection tool:

**Role-Specific Landing Pages:**
| URL | Page Type | Status |
|-----|-----------|--------|
| `https://www.invoicekits.com/for-small-business/` | Landing Page | Pending |
| `https://www.invoicekits.com/for-consultants/` | Landing Page | Pending |
| `https://www.invoicekits.com/compare/` | Comparison Page | Pending |

**Template Showcase Pages:**
| URL | Page Type | Status |
|-----|-----------|--------|
| `https://www.invoicekits.com/templates/clean-slate/` | Template Showcase | Pending |
| `https://www.invoicekits.com/templates/executive/` | Template Showcase | Pending |
| `https://www.invoicekits.com/templates/bold-modern/` | Template Showcase | Pending |
| `https://www.invoicekits.com/templates/classic-professional/` | Template Showcase | Pending |
| `https://www.invoicekits.com/templates/neon-edge/` | Template Showcase | Pending |

**Blog Posts:**
| URL | Page Type | Status |
|-----|-----------|--------|
| `https://www.invoicekits.com/blog/` | Blog Index | Pending |
| `https://www.invoicekits.com/blog/how-to-create-professional-invoice/` | Blog Post | Pending |
| `https://www.invoicekits.com/blog/batch-invoice-generator-guide/` | Blog Post | Pending |
| `https://www.invoicekits.com/blog/freelancer-invoice-tips-get-paid-faster/` | Blog Post | Pending |
| `https://www.invoicekits.com/blog/small-business-invoicing-guide/` | Blog Post | Pending |
| `https://www.invoicekits.com/blog/invoice-vs-receipt-difference/` | Blog Post | Pending |

**Free Tools:**
| URL | Page Type | Status |
|-----|-----------|--------|
| `https://www.invoicekits.com/tools/invoice-calculator/` | Free Tool | Pending |
| `https://www.invoicekits.com/tools/late-fee-calculator/` | Free Tool | Pending |

### SEO TODOs
- [x] Register with Google Search Console
- [x] Add Google Analytics tracking (G-0NR5NZMNBF)
- [x] Create blog content for keyword targeting (5 posts live)
- [x] Set up custom domain (www.invoicekits.com)
- [x] Submit sitemap to Google Search Console - COMPLETED
- [x] Request indexing for core public pages (/, /pricing/, /for-freelancers/, /privacy/, /terms/, /contact/, /help/, /api/docs/) - COMPLETED
- [ ] **Request indexing for remaining 16 pages** (see URLs Pending section above)
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
- QR code linking to public invoice view page

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
77. Blog Post 5: "Invoice vs Receipt: What's the Difference?" - comprehensive guide comparing invoices and receipts
78. Increased keyword density on homepage - added "invoice generator" 4 more times naturally
79. Added BreadcrumbList schema and visual breadcrumb navigation to all internal pages (pricing, help, contact, privacy, terms, API docs, blog list, blog detail)
80. Added FAQPage schema to pricing page (4 FAQs) and help page (10 FAQs) for rich search results
81. Created `/for-freelancers/` landing page with SEO-optimized content targeting freelancers (BreadcrumbList + FAQPage schema, pain points, features, testimonials, pricing)
82. Created `/for-small-business/` landing page with SEO-optimized content targeting small businesses (batch processing, API, recurring invoices focus)
83. Created `/for-consultants/` landing page with SEO-optimized content targeting consultants (hourly billing, retainers, Executive template showcase)
84. Created `/compare/` competitor comparison page with feature comparison table (vs Invoice-Generator.com, Canva, Wave, Zoho Invoice), FAQPage schema
85. Implemented hybrid credits + subscriptions billing model for maximum revenue capture
86. Added credit fields to CustomUser model (credits_balance, free_credits_remaining, total_credits_purchased)
87. Created CreditPurchase model for tracking credit pack purchases
88. Added credit system methods: get_available_credits(), deduct_credit(), add_credits(), is_active_subscriber()
89. Modified can_create_invoice() and increment_invoice_count() for hybrid billing logic
90. Created database migrations for credit system (includes data migration for existing free users)
91. Added CREDIT_PACKS configuration to settings (10/$9, 25/$19, 50/$35)
92. Created credit purchase Stripe checkout flow (one-time payments)
93. Updated Stripe webhook handler for credit purchase completion
94. Created credit purchase templates (credits.html, credits_success.html)
95. Updated billing overview and plans pages for hybrid credit/subscription display
96. Updated dashboard to show credits for credit users, monthly usage for subscribers
97. Created 5 template showcase pages (`/templates/<slug>/`) with SEO meta tags, Product schema, invoice mockups, and CTAs
98. Added template showcase URLs to sitemap and robots.txt
99. Fixed missing `image` field in Product schema on pricing page (GSC validation error)
100. Fixed missing `image` field in Product schema on all 5 template showcase pages
101. Fixed BlogPosting schema - added fallback image when featured_image is empty
102. Fixed Publisher schema - added required `logo` field to Organization
103. Removed unverified `aggregateRating` from SoftwareApplication schema
104. Added `image` and `url` fields to SoftwareApplication schema
105. Fixed robots.txt blocking `/api/docs/` - added explicit `Allow: /api/docs/` rule
106. Fixed 500 error on `/for-small-business/` and `/for-consultants/` pages (invalid `pages:contact` URL reference)
107. Added Bing Webmaster Tools verification endpoint at `/BingSiteAuth.xml`
108. Changed template showcase schema from `Product` to `CreativeWork` on all 5 pages (fixes GSC warnings for missing shippingDetails and hasMerchantReturnPolicy - not applicable to digital templates)
109. Changed pricing page schema from `Product` to `Service` with full OfferCatalog (includes all credit packs and subscriptions, fixes same GSC warnings)
110. Added QR code feature to invoice PDFs - links to public invoice view page where clients can view invoice details and mark as paid
111. Added `public_token` UUID field to Invoice model for secure public access
112. Created public invoice views (PublicInvoiceView, PublicInvoiceMarkPaidView, public_invoice_pdf)
113. Added QR code generation using qrcode library (base64 data URI embedded in PDF)
114. Created public invoice template with Tailwind CSS styling
115. Added QR code section to all 5 PDF templates with template-appropriate styling
116. Added digital signature feature - upload signature image in Company Settings
117. Added `signature` ImageField to Company model with old file cleanup in save()
118. Added signature upload UI to company settings template with live preview
119. Added remove_signature view and URL route
120. Added signature section to all 5 PDF templates with template-specific styling (Clean Slate, Executive, Bold Modern, Classic Professional, Neon Edge)
121. Implemented Team Seats feature for Business tier (3 team seats per company)
122. Created TeamMember and TeamInvitation models with role-based access (Admin/Member)
123. Added `owner` field to Company model with backwards-compatible migration
124. Created team management views (invite, accept, remove, cancel invitation)
125. Created team email service for invitation and welcome emails
126. Created team settings template with seat usage indicator
127. Updated settings navigation to show Team tab for Business tier users
128. Implemented auto-accept invitations on signup/login via signals
129. Updated all invoice views with TeamAwareQuerysetMixin for shared company access
130. Added team-related admin configuration for TeamMember and TeamInvitation models
131. Implemented Premium Templates feature for one-time template purchases
132. Added FREE_TEMPLATES, PREMIUM_TEMPLATES, PREMIUM_TEMPLATE_BUNDLE to settings
133. Added unlocked_templates JSONField and methods to CustomUser model
134. Created TemplatePurchase model for tracking template purchases
135. Created template store views (TemplateStoreView, purchase_template, TemplatePurchaseSuccessView)
136. Updated Stripe webhook handler for template purchase completion
137. Created template store templates (templates.html, templates_success.html)
138. Registered TemplatePurchase in admin with CreditPurchase
139. Created Free SEO Tools: Invoice Calculator and Late Fee Calculator
140. Added InvoiceCalculatorView and LateFeeCalculatorView to invoices/views.py
141. Created `/tools/invoice-calculator/` with line items mode, hourly rate mode, tax/discount, live totals
142. Created `/tools/late-fee-calculator/` with flat fee, percentage, compound interest, payment terms presets
143. Added BreadcrumbList, WebApplication, and FAQPage JSON-LD schemas to both tool pages
144. Added Free Tools section to footer navigation
145. Updated sitemap and robots.txt to include `/tools/` URLs
146. Implemented Affiliate Program with 20% commission on all purchases
147. Created Affiliate, Referral, Commission, AffiliateApplication models
148. Added affiliate dashboard with stats, referral links, and promotional materials
149. Implemented referral tracking via 30-day cookies
150. Connected referral cookies to new user signups via django-allauth signals
151. Integrated commission tracking into Stripe webhook for subscriptions, credit packs, and templates
152. Created affiliate application workflow with admin approval system
153. Added public affiliate program landing page at `/affiliate/program/`
154. Created AffiliateAdmin with earnings display and status management

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
