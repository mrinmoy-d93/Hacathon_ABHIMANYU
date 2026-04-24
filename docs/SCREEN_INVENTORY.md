# KHOJO — Screen Inventory (Phase 5)

Every screen shipped by the Phase 5 frontend, mapped to the Functional
Requirements Specification (FRS) section it satisfies. Screenshots are
placeholders — record them from a running dev build before the final demo.

## Public / Auth

| # | Route | Component | FRS reference | Screenshot |
|---|---|---|---|---|
| 1 | `/` | `app/page.tsx` | FRS §1, §5 (landing) | _placeholder_ |
| 2 | `/register` | `app/register/page.tsx` | FRS §6.1 FR-1.1, FR-1.2, FR-1.4 | _placeholder_ |
| 3 | `/verify-otp` | `app/verify-otp/page.tsx` | FRS §6.1 FR-1.2, FR-1.5, AC-11 | _placeholder_ |

## Community Member (Family)

| # | Route | Component | FRS reference | Screenshot |
|---|---|---|---|---|
| 4 | `/cases` | `app/cases/page.tsx` | FRS §6.2 (landing) | _placeholder_ |
| 5 | `/cases/new/details` | `app/cases/new/details/page.tsx` | FRS §6.2 FR-2.1, FR-2.2, FR-2.5 | _placeholder_ |
| 6 | `/cases/new/photos` | `app/cases/new/photos/page.tsx` | FRS §6.2 FR-2.3, FR-2.4 | _placeholder_ |
| 7 | `/cases/new/processing` | `app/cases/new/processing/page.tsx` | FRS §6.3 FR-3.1..FR-3.9 | _placeholder_ |
| 8 | `/cases/new/result` | `app/cases/new/result/page.tsx` | FRS §6.4 FR-4.1..FR-4.4 | _placeholder_ |
| 9 | `/cases/[id]` | `app/cases/[id]/page.tsx` | FRS §6.4 case status | _placeholder_ |

## Field Worker

| # | Route | Component | FRS reference | Screenshot |
|---|---|---|---|---|
| 10 | `/field-worker/alerts` | `app/field-worker/alerts/page.tsx` | FRS §6.5 FR-5.1 | _placeholder_ |
| 11 | `/field-worker/verify/[matchId]` | `app/field-worker/verify/[matchId]/page.tsx` | FRS §6.5 FR-5.2, FR-5.3, FR-5.4, FR-5.5 | _placeholder_ |

## Administrator (five tabs)

| # | Route | Component | FRS reference | Screenshot |
|---|---|---|---|---|
| 12 | `/admin/overview` | `app/admin/overview/page.tsx` | FRS §6.6 Tab 1 | _placeholder_ |
| 13 | `/admin/cases` | `app/admin/cases/page.tsx` | FRS §6.6 Tab 2 | _placeholder_ |
| 14 | `/admin/field-workers` | `app/admin/field-workers/page.tsx` | FRS §6.6 Tab 3 | _placeholder_ |
| 15 | `/admin/ai-settings` | `app/admin/ai-settings/page.tsx` | FRS §6.6 Tab 4 | _placeholder_ |
| 16 | `/admin/audit-log` | `app/admin/audit-log/page.tsx` | FRS §6.6 Tab 5 | _placeholder_ |

## Shared components

| Component | Purpose | FRS reference |
|---|---|---|
| `components/AppShell.tsx` | Top-nav, role badge, logout, mobile menu | UX |
| `components/AuthHydrationGuard.tsx` | Gates pages on Zustand hydration + role | FRS §6.1 |
| `components/AIBadge.tsx` | "AI estimate — verify with officer" disclaimer | FR-4.4 |
| `components/ConfidenceBar.tsx` | Tiered colour-coded confidence bar | FR-4.2 |
| `components/PhotoCompare.tsx` | Side-by-side original + aged / candidate | FR-4.1 |
| `components/StepIndicator.tsx` | 4-step progress for case registration | UX |
| `components/NotMatchModal.tsx` | Mandatory photo upload modal | FR-5.4 |
| `components/Acronym.tsx` | Per-page first-occurrence acronym expansion | FR-4.5, AC-7 |

## Global state

- **Error boundary**: `app/error.tsx` — friendly retry + "Send feedback" link per NFR-3.
- **Not-found page**: `app/not-found.tsx` — keyed to the same palette and AppShell.
- **Toasts**: sonner, mounted globally from `app/layout.tsx`.
- **TanStack Query Devtools**: enabled in development only.
