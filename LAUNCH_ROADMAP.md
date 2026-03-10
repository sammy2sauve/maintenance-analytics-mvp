# TrueSignal — Launch Roadmap

> Last updated: March 2026

---

## Where We Are

The core product is built and demo-ready. Three-page analytics dashboard, predictive failure engine, PM optimization, live KPI tracking, auth (signup/login/JWT), and a marketing landing page — all working. Platform is ready to show a customer.

---

## Phase 1 — MVP Polish ✅ COMPLETE

| # | Task | Status |
|---|------|--------|
| 1 | Logo / branding (EKG waveform SVG) | ✅ Done |
| 2 | Asset type encoding (ASSET-XXX → real types) | ✅ Done |
| 3 | MAINT-XXX / ASSET-XXX ID mismatch | ✅ Done |
| 4 | Date slicer working on Overview | ✅ Done |
| 5 | Urgency histogram shows all assets | ✅ Done |
| 6 | Landing page + Auth (signup / login / JWT) | ✅ Done |

---

## Phase 2 — MaintainX Integration ✅ MOSTLY COMPLETE

**Positioning:** *"Keep using MaintainX for work orders. Connect TrueSignal to get failure predictions, PM optimization, and KPI intelligence your MaintainX dashboard can't show you."*

| # | Task | Status |
|---|------|--------|
| 1 | **Settings page** — enter MaintainX API key after signup | ✅ Done |
| 2 | **MaintainX adapter** — pulls `/workorders` + `/assets` → normalized schema | ✅ Done |
| 3 | **Sync on demand + auto-sync on load** — Sync button in nav, runs pipeline after fetch | ✅ Done |
| 4 | **Multi-tenant scoping** — Org → Location → User, API key on Location, all data scoped by location_id | ✅ Done |
| 5 | **Empty state / onboarding** — new users see "Connect your CMMS" instead of stale data | ✅ Done |
| 6 | **PM status tracking** — mark suggestions as Implemented when a PM is completed in MaintainX | 🔲 Next |

### What PM status tracking means
When a tech completes a PM work order in MaintainX:
1. User hits Sync (or auto-sync on next load)
2. Adapter fetches the new completed PM WO
3. Pipeline matches it to a pending suggestion for that asset (by asset_id + completion date after suggestion_date)
4. Suggestion status flips to `implemented`
5. Cost Savings page shows the updated ring counts and waterfall chart

No webhook needed for MVP — polling on sync is sufficient.

### Auth approach
- **MVP:** API key — user generates in MaintainX Settings → Integrations → pastes into TrueSignal once.
- **Post-launch:** Upgrade to OAuth ("Connect MaintainX" button) once there are real customers.

### Adapter pattern (scales to all CMMS)
```
MaintainX adapter ─┐
Limble adapter    ─┤─→ normalized work_orders schema → pipeline → dashboard
UpKeep adapter    ─┤
Fiix adapter      ─┘
```

---

## Phase 3 — Pre-Launch Polish (Before First Customer)

| # | Task | Status | Detail |
|---|------|--------|--------|
| 1 | **Reset password** | 🔲 Todo | Forgot password flow — email with reset link. Needs domain + email service (Resend) first. |
| 2 | **Demo account + demo data** | 🔲 Todo | Locked `demo@truesignal.io` account. Meridian Medical Center plant is the demo data — needs a locked read-only account wired to it. |
| 3 | **Realistic cost savings data** | ✅ Done | Meridian plant has varied savings, real asset types, real failure patterns. |
| 4 | **Empty state / onboarding** | ✅ Done | New users see "Connect your CMMS" prompt. |

---

## Phase 4 — Commercial Launch

| # | Task | Detail |
|---|------|--------|
| 1 | **Database migration** | SQLite → hosted Postgres (Railway, Supabase, or Neon) |
| 2 | **Deployment** | Frontend → Vercel. Backend → Railway or Fly.io. Custom domain + SSL. |
| 3 | **Legal** | LLC formation, MSA/SaaS ToS, Data Processing Agreement (DPA) |
| 4 | **Billing + pricing** | Stripe integration — subscription management, per-seat or per-asset pricing tiers. Payment wall before dashboard access after trial ends. |

---

## Phase 5 — Growth Features

These ship after the first paying customer. Each one increases retention and upsell potential.

### Reporting
| # | Task | Detail |
|---|------|--------|
| 1 | **PDF report — Overview** | One-click export of fleet health score, risk breakdown, KPI summary, and insights for the selected time range |
| 2 | **PDF report — Asset Health** | Full asset risk list, urgency breakdown, top critical assets with recommendations |
| 3 | **PDF report — Cost Savings** | PM suggestion list, cumulative savings waterfall, status summary. Ready to hand to leadership. |
| 4 | **Custom reports** | User selects which sections to include (fleet health, risk breakdown, KPIs, PM suggestions, cost savings). Choose date range and output format (PDF or CSV). Saves configuration as a named report template. |

### Notifications & Scheduled Delivery
| # | Task | Detail |
|---|------|--------|
| 5 | **Email alerts** | Configurable triggers: new CRITICAL asset, weekly fleet digest, PM suggestion accepted. Uses Resend. |
| 6 | **Recurring report emails** | Schedule any saved report template to be emailed automatically — daily, weekly, or monthly. User sets recipients and delivery day/time. Built on top of the custom reports feature. |
| 7 | **One-time report emails** | Send a generated report to any email address on-demand from within the dashboard. Useful for sharing with stakeholders who don't have TrueSignal logins. |

### Dashboard Customization
| # | Task | Detail |
|---|------|--------|
| 8 | **Widget layout customization** | Drag-and-drop dashboard layout — users pin/hide/reorder cards and charts. Saved per user account. |
| 9 | **Saved views** | Users name and save their preferred date range + visible widget set. Switch between views with one click (e.g. "Weekly Leadership View", "Daily Ops View"). |

### AI Assistant
| # | Task | Detail |
|---|------|--------|
| 5 | **In-app AI chatbot** | Floating chat widget across all dashboard pages. Answers questions about what the user is seeing, guides them through standard workflows (e.g. "how do I action a PM suggestion?"), and links to documentation. Powered by Claude API with platform context injected. |
| 6 | **Documentation site** | Public docs at `docs.truesignal.io` — getting started, connecting MaintainX, understanding risk scores, reading the cost savings page, FAQ. The AI chatbot pulls from these docs. |

### CMMS Expansion
| # | Task | Detail |
|---|------|--------|
| 7 | **Additional CMMS adapters** | Limble, UpKeep, Fiix — same adapter pattern as MaintainX |
| 8 | **OAuth for MaintainX** | Replace API key paste with "Connect MaintainX" button |
| 9 | **CMMS webhook for PM status** | MaintainX pushes Accepted/Implemented back when PMs are actioned |

---

## Security & Legal Compliance

These items run in parallel with Phase 3–4 and must be resolved before signing any paying customer.

### Legal Documents
| # | Task | Detail |
|---|------|--------|
| 1 | **Terms & Conditions / Terms of Service** | User rights, prohibited uses, liability limits, termination clauses. Required before any paid plan goes live. Use a SaaS attorney or a vetted template service (Bonterms, Clerky). |
| 2 | **Privacy Policy** | What data you collect, how it's stored, who it's shared with, user rights (deletion, export). Required by law in most jurisdictions. |
| 3 | **Data Processing Agreement (DPA)** | Required by GDPR/CCPA customers. Governs how TrueSignal handles customer work order data on their behalf. |
| 4 | **Master Service Agreement (MSA)** | Enterprise contract for B2B deals. Covers SLAs, data ownership, indemnification, confidentiality. |

### Data Security
| # | Task | Detail |
|---|------|--------|
| 5 | **Hosted database security** | Data security is largely inherited from the hosting provider. Supabase, Railway, and Neon all include encryption at rest and in transit, access controls, and backups. Choose a provider, document it in your DPA. |
| 6 | **Secrets management** | Move JWT secret key and API keys out of source code into environment variables. Use hosting provider's secrets manager (Railway/Fly.io have native support). |
| 7 | **API security hardening** | Rate limiting on auth endpoints, HTTPS-only, CORS locked to production domain, no sensitive data in logs. |
| 8 | **SOC 2 Type II** | Long-term goal — required by enterprise customers and procurement teams. Start tracking the controls now (access logs, change management, incident response). Formal audit comes when you have the revenue to justify it (~$500K ARR). |

---

## Legal Structure

```
SignalGroup LLC (Holding Company)
  ├── TrueSignal LLC (maintenance analytics SaaS)
  └── [Future Company] LLC (manufacturing data — TBD)
```

- Each subsidiary is liability-isolated — one can't affect the other
- Separate valuations, fundraising, and potential exits per entity
- Start LLC formation with a business attorney — do not DIY

---

## Shortest Path to First Paying Customer

```
Realistic demo data + demo account
  → MaintainX integration (API key, daily sync)
  → Multi-tenant data scoping
  → Deploy to hosted URL + custom domain
  → Billing (Stripe)
  → Legal (LLC + MSA) — start now, runs in parallel
  → Reset password (needs domain + email service)
  → First customer
```

**Estimated:** 3–4 weeks of focused work.
