# InvoiceKits - Project Status

## Live Site
**URL:** https://web-production-faa7d.up.railway.app/

**Deployment:** Railway with Nixpacks builder

---

## Current Status

### Working Features
- Landing page with pricing display
- User authentication (signup/login/logout via django-allauth)
- User dashboard with invoice stats
- Invoice creation with dynamic line items
- PDF generation with 5 template styles (WeasyPrint)
- Invoice list with search and status filters
- Invoice detail view
- Batch CSV upload (for Professional+ plans)
- CSV template download
- Company profile management
- Billing/subscription UI pages
- REST API endpoints with API key authentication
- Usage tracking per user

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

### High Priority
- [ ] **Stripe Integration:** Replace placeholder price IDs in `apps/billing/views.py:67-71`:
  ```python
  price_ids = {
      'starter': 'price_starter_monthly',      # REPLACE with actual Stripe price ID
      'professional': 'price_professional_monthly',
      'business': 'price_business_monthly',
  }
  ```
- [ ] **Watermark on Free Tier PDFs:** `apps/invoices/services/pdf_generator.py` - add watermark logic when `user.subscription_tier == 'free'`
- [ ] **Stripe Subscription Cancellation on Account Delete:** `apps/accounts/views.py:88` has TODO

### Medium Priority
- [ ] **Google AdSense Integration:** Add to landing page sidebar, dashboard (free users only)
- [ ] **Email Notifications:**
  - Welcome email on signup
  - Invoice sent notifications
  - Payment receipts
- [ ] **Social Authentication:** Configure Google and GitHub OAuth providers
- [ ] **Invoice Email Sending:** Send invoices directly to clients via email

### Lower Priority
- [ ] **Team Seats:** Business plan includes 3 team seats (model and UI not implemented)
- [ ] **Enterprise Tier:** Custom pricing, white-label, dedicated support
- [ ] **Premium Templates:** Individual template purchases ($4.99 each)
- [ ] **Affiliate Program:** Referral tracking (20% commission)
- [ ] **QR Code for Payment:** Optional on invoices
- [ ] **Digital Signature Field:** On invoice PDFs
- [ ] **Invoice Edit Page:** `templates/invoices/edit.html` - needs to be created
- [ ] **Invoice Delete Confirmation:** `templates/invoices/delete_confirm.html` - needs to be created
- [ ] **Batch Result Page:** `templates/invoices/batch_result.html` - needs to be created
- [ ] **Account Delete Confirmation:** `templates/accounts/delete_confirm.html` - needs to be created

---

## Environment Variables Required

### Currently Set on Railway
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Railway)
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `ALLOWED_HOSTS` - `.railway.app` added automatically

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
DOMAIN=invoicegenerator.pro
```

---

## Project Structure

```
invoice_generator/
├── config/
│   ├── settings/
│   │   ├── base.py          # Core settings
│   │   ├── development.py   # Local dev
│   │   └── production.py    # Railway production
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/            # User model, dashboard, settings
│   ├── billing/             # Subscription & Stripe
│   ├── invoices/            # Invoice CRUD, PDF generation
│   │   └── services/
│   │       ├── pdf_generator.py
│   │       └── batch_processor.py
│   ├── companies/           # Company profiles
│   └── api/                 # REST API (DRF)
├── templates/
│   ├── account/             # allauth templates (login, signup)
│   ├── dashboard/
│   ├── invoices/
│   │   └── pdf/             # 5 PDF templates
│   ├── billing/
│   ├── landing/
│   └── settings/
├── static/
├── nixpacks.toml            # Railway build config
└── railway.json             # Railway deploy config
```

---

## Key Files

| File | Purpose |
|------|---------|
| `config/settings/base.py` | Subscription tiers, invoice templates, core config |
| `config/settings/production.py` | Railway-specific settings, security |
| `apps/accounts/models.py` | CustomUser with subscription tracking |
| `apps/invoices/services/pdf_generator.py` | WeasyPrint PDF generation |
| `apps/billing/views.py` | Stripe checkout flow (needs price IDs) |
| `apps/api/views.py` | REST API endpoints |
| `nixpacks.toml` | Nix packages for WeasyPrint (pango, cairo, etc.) |

---

## Subscription Tiers

| Tier | Price | Invoices/mo | Features |
|------|-------|-------------|----------|
| Free | $0 | 5 | 1 template, watermark |
| Starter | $9 | 50 | 2 templates, no watermark |
| Professional | $29 | 200 | All templates, batch upload |
| Business | $79 | Unlimited | API access (1000 calls/mo) |

---

## Recent Fixes (Deployment History)

1. Fixed ALLOWED_HOSTS to include `.railway.app`
2. Removed placeholder Stripe keys causing djstripe crash
3. Switched from Ubuntu apt packages to Nix packages for WeasyPrint dependencies
4. Removed healthcheck (startup exceeds timeout)
5. Fixed template URL namespaces (`landing:index` -> `invoices:landing`)
6. Fixed allauth URL names (`accounts:login` -> `account_login`)
7. Disabled email verification (SMTP not configured)
