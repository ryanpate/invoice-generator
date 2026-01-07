# InvoiceKits - Project Status

## Live Site
**URL:** https://web-production-faa7d.up.railway.app/

**Domain:** invoicekits.com (pending DNS configuration)

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
- Usage tracking per user
- Admin panel (/admin/) with superuser auto-creation from env vars
- SEO optimizations (meta tags, Open Graph, Twitter Cards, Schema.org, sitemap, robots.txt)

### Suppressed/Disabled Features

| Feature | Status | Reason | To Enable |
|---------|--------|--------|-----------|
| Email Verification | Disabled | No SMTP credentials | Set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` env vars, then change `ACCOUNT_EMAIL_VERIFICATION` to `'mandatory'` in `config/settings/production.py` |
| Stripe Payments | Non-functional | No Stripe keys/price IDs | Add `STRIPE_LIVE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` env vars. Create price IDs in Stripe Dashboard and update `billing/views.py:67-71` |
| djstripe | Conditionally disabled | Only loads if Stripe keys exist | Set `STRIPE_TEST_SECRET_KEY` or `STRIPE_LIVE_SECRET_KEY` |
| S3 Media Storage | Disabled | No AWS credentials | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` |
| Celery/Redis | Disabled | No Redis configured | Add Redis service on Railway, set `REDIS_URL` env var |
| Social Auth (Google/GitHub) | UI Only | OAuth not configured | Configure in django-allauth + provider settings |
| Healthcheck | Removed | Startup time exceeds Railway timeout | Re-add to `railway.json` if startup is optimized |

---

## Not Yet Implemented (TODOs)

### Critical - Revenue Blocking
- [ ] **Stripe Integration:** Replace placeholder price IDs in `apps/billing/views.py:67-71`:
  ```python
  price_ids = {
      'starter': 'price_starter_monthly',      # REPLACE with actual Stripe price ID
      'professional': 'price_professional_monthly',
      'business': 'price_business_monthly',
  }
  ```
- [ ] **Stripe Webhook Handler:** Ensure subscription lifecycle events are handled
- [ ] **Watermark on Free Tier PDFs:** `apps/invoices/services/pdf_generator.py` - add watermark logic when `user.subscription_tier == 'free'`

### High Priority - Core Functionality
- [x] **Invoice Edit Page:** `templates/invoices/edit.html` - COMPLETED
- [x] **Invoice Delete Confirmation:** `templates/invoices/delete_confirm.html` - COMPLETED
- [x] **Batch Result Page:** `templates/invoices/batch_result.html` - COMPLETED
- [x] **Account Delete Confirmation:** `templates/accounts/delete_confirm.html` - COMPLETED
- [ ] **Stripe Subscription Cancellation on Account Delete:** `apps/accounts/views.py:88` has TODO
- [ ] **Custom Domain Setup:** Configure invoicekits.com DNS to point to Railway

### Medium Priority - Growth & Marketing
- [ ] **Google Search Console:** Add verification meta tag or DNS record
- [ ] **Google Analytics:** Add GA4 tracking code to `templates/base.html`
- [ ] **Google AdSense Integration:** Add to landing page sidebar, dashboard (free users only)
- [ ] **Email Notifications:**
  - Welcome email on signup
  - Invoice sent notifications
  - Payment receipts
- [ ] **Social Authentication:** Configure Google and GitHub OAuth providers
- [ ] **Invoice Email Sending:** Send invoices directly to clients via email
- [ ] **Blog/Content Marketing:** Create `/blog/` section for SEO content

### Lower Priority - Feature Expansion
- [ ] **Team Seats:** Business plan includes 3 team seats (model and UI not implemented)
- [ ] **Enterprise Tier:** Custom pricing, white-label, dedicated support
- [ ] **Premium Templates:** Individual template purchases ($4.99 each)
- [ ] **Affiliate Program:** Referral tracking (20% commission)
- [ ] **QR Code for Payment:** Optional on invoices
- [ ] **Digital Signature Field:** On invoice PDFs
- [ ] **Recurring Invoices:** Auto-generate invoices on schedule
- [ ] **Client Portal:** Allow clients to view/pay invoices online
- [ ] **Multi-language Support:** i18n for international users

### SEO Improvements - Future
- [ ] **Dynamic Sitemap:** Add invoice public links to sitemap (if public sharing enabled)
- [ ] **Blog Posts:** Create keyword-rich content for organic traffic
- [ ] **Backlink Outreach:** Partner with freelancer/small business sites
- [ ] **Page Speed Optimization:** Lazy loading, image optimization, CDN
- [ ] **Core Web Vitals:** Monitor and improve LCP, FID, CLS scores

---

## Environment Variables Required

### Currently Set on Railway
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Railway)
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `ALLOWED_HOSTS` - `.railway.app` added automatically
- `DJANGO_SUPERUSER_EMAIL` - Admin user email
- `DJANGO_SUPERUSER_PASSWORD` - Admin user password

### Need to Configure
```bash
# Email (required for email verification)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe (required for payments)
STRIPE_LIVE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3 (optional - for media file storage)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...

# Redis (optional - for Celery async tasks)
REDIS_URL=redis://...

# Custom domain (optional)
DOMAIN=invoicekits.com

# Analytics (optional)
GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
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
│   │       └── batch_processor.py # CSV batch processing
│   ├── companies/           # Company profiles & branding
│   └── api/                 # REST API (DRF)
├── templates/
│   ├── account/             # allauth templates (login, signup)
│   ├── dashboard/
│   ├── invoices/
│   │   └── pdf/             # 5 PDF templates
│   ├── billing/
│   ├── landing/             # Home page with FAQ
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
| `config/settings/production.py` | Railway-specific settings, security, CSRF |
| `config/urls.py` | Main URL routing + sitemap + robots.txt views |
| `apps/accounts/models.py` | CustomUser with subscription tracking |
| `apps/invoices/models.py` | Invoice model with invoice_name field |
| `apps/invoices/forms.py` | InvoiceForm with invoice_name field |
| `apps/invoices/services/pdf_generator.py` | xhtml2pdf PDF generation |
| `apps/billing/views.py` | Stripe checkout flow (needs price IDs) |
| `apps/api/views.py` | REST API endpoints |
| `templates/base.html` | Base template with SEO meta tags + Schema.org |
| `templates/landing/index.html` | Landing page with FAQ + FAQPage schema |
| `railway.json` | Railway deploy config with startCommand |
| `nixpacks.toml` | Nix packages for build |

---

## Subscription Tiers

| Tier | Price | Invoices/mo | Features |
|------|-------|-------------|----------|
| Free | $0 | 5 | 1 template, watermark |
| Starter | $9 | 50 | 2 templates, no watermark |
| Professional | $29 | 200 | All templates, batch upload |
| Business | $79 | Unlimited | API access (1000 calls/mo) |

---

## SEO Implementation

### Technical SEO (Completed)
- **Meta Tags:** Title, description, keywords, canonical URL, robots meta
- **Open Graph:** og:type, og:url, og:title, og:description, og:site_name
- **Twitter Cards:** twitter:card, twitter:title, twitter:description
- **Schema.org Markup:**
  - SoftwareApplication schema on all pages (`templates/base.html`)
  - FAQPage schema on landing page (`templates/landing/index.html`)
- **Sitemap:** XML sitemap at `/sitemap.xml` (static pages: /, /pricing/)
- **Robots.txt:** Available at `/robots.txt` with proper allow/disallow rules
- **FAQ Section:** 6 keyword-rich Q&As on landing page

### SEO URLs
| URL | Purpose |
|-----|---------|
| `/sitemap.xml` | XML sitemap for search engines |
| `/robots.txt` | Search engine crawler instructions |
| `/#faq` | FAQ section with structured data |

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
- [ ] Register with Google Search Console
- [ ] Add Google Analytics tracking
- [ ] Create blog content for keyword targeting
- [ ] Build quality backlinks
- [ ] Monitor Core Web Vitals
- [ ] Set up custom domain (invoicekits.com)

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
- Optional watermark (for free tier - TODO)

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

### Required for Production
1. Set all environment variables listed above
2. Configure Stripe products and price IDs
3. Set up custom domain DNS
4. Enable HTTPS (automatic on Railway)
