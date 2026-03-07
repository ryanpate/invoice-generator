# InvoiceKits iOS App - Design Document

**Date:** 2026-03-06
**Status:** Approved

## Overview

Native SwiftUI iOS/iPadOS app for InvoiceKits, targeting iOS 17+. Universal (iPhone + iPad). Lives in `ios/InvoiceKits/` subdirectory of the existing repo. Communicates with the Django backend via a new REST API v2 with JWT authentication.

## Approach

**Pure native SwiftUI** — no WKWebView, no React Native. Every screen uses native iOS components. This maximizes App Store approval odds (Guideline 4.2) and delivers the best user experience.

## Architecture

```
iOS App (SwiftUI)
├── SwiftUI Views
├── StoreKit 2 (IAP)
├── LocalAuthentication (Face ID / Touch ID)
├── Service Layer (APIClient, AuthManager, StoreManager, CacheManager)
└── SwiftData (Local Cache)
        │
        │ HTTPS (JWT Auth)
        ▼
Django Backend (Expanded API v2)
├── /api/v2/auth/       (login, register, social, refresh)
├── /api/v2/invoices/   (CRUD, PDF, send, AI generate, voice)
├── /api/v2/time/       (entries, timers)
├── /api/v2/recurring/  (CRUD, toggle)
├── /api/v2/reminders/  (settings, toggle)
├── /api/v2/late-fees/  (settings, toggle)
├── /api/v2/company/    (profile, logo, signature)
├── /api/v2/billing/    (usage, plans, receipt validation)
└── /api/v2/clients/    (analytics, history)
```

### Key Architectural Decisions

- **API v2** alongside existing v1. JWT auth (djangorestframework-simplejwt) instead of API keys.
- **SwiftData** for read-only offline cache of invoices, time entries, company data.
- **JWT tokens** stored in Keychain with biometric access control.
- **StoreKit 2** for all IAP. Server-side receipt validation via Apple App Store Server API.
- **Two Xcode targets:** main app + widget extension (Live Activities / Dynamic Island).

## v1 Feature Scope

### Included
- Invoice CRUD with PDF preview (PDFKit) and native share sheet
- AI text-to-invoice + voice-to-invoice (AVFoundation -> backend -> Claude)
- Time tracking with Live Activities / Dynamic Island
- Recurring invoices (CRUD, pause/resume, generate now)
- Payment reminders (settings, per-invoice toggle)
- Late fees (settings, per-invoice toggle)
- Company profile with camera/photo picker for logo + signature
- Client payment rating (A-F) on invoice creation
- Dashboard with stats and active timer
- Face ID / Touch ID app lock with configurable grace period
- StoreKit 2 IAP (Pro/Business monthly+annual, credit packs)
- Billing sync between Stripe (web) and Apple (iOS)
- Push notifications via APNs
- Read-only offline via SwiftData cache
- Sign in with Apple + Google + email/password
- iPad NavigationSplitView (sidebar + detail)

### Excluded from v1
- Team management
- Batch CSV upload
- Client portal
- Affiliate program

## Authentication

### Login Methods
1. Sign in with Apple (required by Apple since we offer social login)
2. Google Sign-In
3. Email + password

### JWT Flow
- Access token: 15-minute expiry
- Refresh token: 30-day expiry
- Both stored in Keychain with biometric access control (when Face ID enabled)
- Token refresh is transparent to the user

### Face ID / Touch ID
```
App Opens
    -> Has JWT in Keychain?
        -> NO: Show Sign In screen
        -> YES: Face ID enabled?
            -> NO: Go straight to app
            -> YES: Prompt Face ID
                -> SUCCESS: Unlock Keychain, load app
                -> FAIL: Retry or device passcode fallback
                -> CANCEL: Stay on locked screen with retry
    -> Token expired?
        -> Use refresh token for new access token
        -> Refresh also expired? -> Sign In screen
```

### Face ID Settings
- Require Face ID: toggle (default ON)
- Lock after background: Immediately / 1 min / 5 min / 15 min
- Keychain stored with `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly` and `.biometryCurrentSet`

## Screen Map & Navigation

TabView with 4 tabs, plus modal flows:

```
TabView
├── Invoices (Tab 1)
│   ├── Invoice List (search, status filter)
│   ├── Invoice Detail (status, actions, reminder/late fee info)
│   ├── Invoice Create/Edit (sheet)
│   │   ├── AI Generate (collapsible section)
│   │   ├── Voice-to-Invoice (mic button)
│   │   └── Client Payment Rating (auto-loads on email entry)
│   ├── PDF Preview (PDFKit, share sheet)
│   └── Recurring Invoices (list, create, edit, detail)
│
├── Time (Tab 2)
│   ├── Active Timer (top card, always visible when running)
│   ├── Time Entry List (search, filters)
│   ├── Manual Entry (sheet)
│   └── Bill Time (select entries -> create invoice)
│
├── Dashboard (Tab 3)
│   ├── Stats Cards (invoices, revenue, outstanding)
│   ├── Active Timer Widget
│   ├── AI Generations Remaining
│   └── Recent Invoices
│
└── Settings (Tab 4)
    ├── Company Profile (name, logo, signature upload)
    ├── Payment Reminders (schedule config)
    ├── Late Fees (type, amount, grace period)
    ├── Subscription / IAP Management
    ├── Account (email, password, delete)
    └── App Settings (Face ID toggle, appearance)

Modal Flows:
├── Sign In (Apple / Google / Email)
├── Sign Up (Apple / Google / Email)
└── Face ID Prompt (on app launch)
```

### Navigation Patterns
- `NavigationStack` within each tab (iPhone)
- `NavigationSplitView` on iPad (sidebar + detail, collapses on iPhone)
- `.sheet()` for create/edit flows
- `.fullScreenCover()` for auth and Face ID gate
- Swipe-to-delete on list views
- Pull-to-refresh on all lists
- Context menus (long press) for quick actions (duplicate, send, mark paid)

## Native iOS Features

| Feature | Framework | Notes |
|---------|-----------|-------|
| Face ID / Touch ID | LocalAuthentication | App unlock + Keychain protection |
| PDF Preview | PDFKit | Native PDF rendering |
| Share Invoices | UIActivityViewController | AirDrop, Mail, Messages, Files |
| Voice-to-Invoice | AVFoundation | AVAudioRecorder, send to backend |
| AI Generator | Native TextEditor | Text to backend /ai-generate/ |
| Timer | ActivityKit | Live Activities + Dynamic Island |
| Camera/Photos | PhotosUI | PhotosPicker for logo/signature |
| IAP | StoreKit 2 | Subscriptions + consumables |
| Offline Cache | SwiftData | Read-only local cache |
| Push Notifications | APNs + UserNotifications | Payment, reminder, recurring events |
| Haptics | UIImpactFeedbackGenerator | Timer, status changes, actions |
| Pull to Refresh | .refreshable {} | All list views |
| Swipe Actions | .swipeActions {} | Delete, duplicate, mark paid |
| Search | .searchable() | Invoice and time entry lists |
| Keychain | Security framework | JWT with biometric access control |

## API v2 Endpoints

All under `/api/v2/` with JWT auth (~45 endpoints total).

### Authentication
```
POST /api/v2/auth/register/
POST /api/v2/auth/login/
POST /api/v2/auth/token/refresh/
POST /api/v2/auth/social/apple/
POST /api/v2/auth/social/google/
DELETE /api/v2/auth/account/
```

### Invoices
```
GET    /api/v2/invoices/
POST   /api/v2/invoices/
GET    /api/v2/invoices/{id}/
PUT    /api/v2/invoices/{id}/
DELETE /api/v2/invoices/{id}/
GET    /api/v2/invoices/{id}/pdf/
POST   /api/v2/invoices/{id}/send/
POST   /api/v2/invoices/{id}/mark-paid/
POST   /api/v2/invoices/{id}/mark-sent/
POST   /api/v2/invoices/{id}/toggle-reminders/
POST   /api/v2/invoices/{id}/toggle-late-fees/
POST   /api/v2/invoices/{id}/make-recurring/
```

### AI Generator
```
POST /api/v2/ai/generate/
POST /api/v2/ai/voice-generate/
```

### Time Tracking
```
GET    /api/v2/time/entries/
POST   /api/v2/time/entries/
PUT    /api/v2/time/entries/{id}/
DELETE /api/v2/time/entries/{id}/
POST   /api/v2/time/entries/bill/
POST   /api/v2/time/timer/start/
POST   /api/v2/time/timer/{id}/stop/
POST   /api/v2/time/timer/{id}/discard/
GET    /api/v2/time/timer/status/
```

### Recurring Invoices
```
GET    /api/v2/recurring/
POST   /api/v2/recurring/
GET    /api/v2/recurring/{id}/
PUT    /api/v2/recurring/{id}/
DELETE /api/v2/recurring/{id}/
POST   /api/v2/recurring/{id}/toggle/
POST   /api/v2/recurring/{id}/generate/
```

### Company & Settings
```
GET    /api/v2/company/
PUT    /api/v2/company/
POST   /api/v2/company/logo/
DELETE /api/v2/company/logo/
POST   /api/v2/company/signature/
DELETE /api/v2/company/signature/
GET    /api/v2/settings/reminders/
PUT    /api/v2/settings/reminders/
GET    /api/v2/settings/late-fees/
PUT    /api/v2/settings/late-fees/
```

### Billing & IAP
```
GET    /api/v2/billing/usage/
GET    /api/v2/billing/entitlements/
POST   /api/v2/billing/verify-receipt/
POST   /api/v2/billing/register-device/
POST   /api/v2/billing/apple-notifications/
```

### Client Analytics
```
GET /api/v2/clients/stats/?email={email}
```

## StoreKit 2 & Billing Sync

### Product IDs
```
Subscriptions (auto-renewable):
  com.invoicekits.pro.monthly        $12/mo
  com.invoicekits.pro.annual         $115/year
  com.invoicekits.business.monthly   $49/mo
  com.invoicekits.business.annual    $470/year

Consumables (credit packs):
  com.invoicekits.credits.10         $9
  com.invoicekits.credits.25         $19
  com.invoicekits.credits.50         $35
```

### Sync Rules
- `payment_source` field on CustomUser: `'stripe'` or `'apple'`
- iOS purchase -> send JWS receipt to backend -> verify with Apple -> update user tier
- Web (Stripe) subscribers see their active tier in iOS without IAP prompt
- Apple Server Notifications v2 at `/api/v2/billing/apple-notifications/` for renewals, cancellations, refunds
- Same price on both platforms (absorb Apple's 30% cut)
- Credit packs are consumable IAP — credits added after server verification

## Push Notifications

### Events
| Event | When |
|-------|------|
| Invoice paid | Client pays or marks paid |
| Reminder sent | Daily reminder task fires |
| Late fee applied | Daily late fee task fires |
| Recurring generated | Recurring task fires |
| Subscription expiring | 3 days before expiry |

### Implementation
- Django sends via APNs (HTTP/2) using `django-push-notifications`
- Device token registered at `/api/v2/billing/register-device/` after login
- Silent push for background data sync when invoice state changes on web
- Permission requested after first invoice created (not on launch)

## Xcode Project Structure

```
ios/InvoiceKits/
├── InvoiceKits.xcodeproj
├── InvoiceKits/
│   ├── App/
│   │   ├── InvoiceKitsApp.swift
│   │   ├── AppState.swift
│   │   └── Constants.swift
│   ├── Models/
│   │   ├── Invoice.swift
│   │   ├── LineItem.swift
│   │   ├── TimeEntry.swift
│   │   ├── ActiveTimer.swift
│   │   ├── RecurringInvoice.swift
│   │   ├── Company.swift
│   │   └── User.swift
│   ├── Services/
│   │   ├── APIClient.swift
│   │   ├── AuthManager.swift
│   │   ├── BiometricManager.swift
│   │   ├── StoreManager.swift
│   │   ├── CacheManager.swift
│   │   ├── NotificationManager.swift
│   │   └── KeychainManager.swift
│   ├── Views/
│   │   ├── Auth/
│   │   ├── Invoices/
│   │   ├── TimeTracking/
│   │   ├── Recurring/
│   │   ├── Dashboard/
│   │   └── Settings/
│   ├── Components/
│   ├── Extensions/
│   ├── Widgets/
│   └── Resources/
├── InvoiceKitsTests/
└── InvoiceKitsWidgetExtension/
```

Two targets: main app + widget extension (Live Activities / Dynamic Island).

## App Store Approval Strategy

| Guideline | How Addressed |
|-----------|---------------|
| 4.2 Minimum Functionality | 100% native SwiftUI, no WKWebView |
| 3.1.1 IAP Required | All purchases via StoreKit 2 |
| 4.8 Sign in with Apple | Offered alongside Google and email |
| 2.1 App Completeness | No placeholders, all features functional |
| 5.1.1 Data Collection | Privacy Nutrition Labels declared |
| 2.4.5 Push Notifications | Contextual prompt, not on first launch |
| 5.1.2 Data Use | Privacy policy at invoicekits.com/privacy/ |

### Privacy Nutrition Labels
| Data Type | Usage | Linked to Identity |
|-----------|-------|--------------------|
| Email Address | Account, notifications | Yes |
| Name | Account | Yes |
| Payment Info | IAP (Apple handled) | No |
| Photos | Logo/signature upload | Yes |
| Audio Data | Voice-to-invoice (not stored) | No |
| Usage Data | Analytics, AI count | Yes |
| Identifiers | APNs device token | Yes |

### App Store Metadata
- **Name:** InvoiceKits
- **Subtitle:** AI Invoice Generator & Timer
- **Category:** Business (primary), Finance (secondary)
- **Screenshots:** iPhone 6.7" + 6.5", iPad 12.9"
- **Support:** universal (iPhone + iPad)
- **Deployment target:** iOS 17.0+
