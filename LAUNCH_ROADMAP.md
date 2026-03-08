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

## Phase 2 — Pre-Launch Polish (Before First Customer)

| # | Task | Detail |
|---|------|--------|
| 1 | **Reset password** | Forgot password flow — email with reset link. Needs domain + email service (Resend) first. |
| 2 | **Demo account + demo data** | Locked `demo@truesignal.io` account with realistic synthetic data. Used for sales calls and self-guided prospects. |
| 3 | **Realistic cost savings data** | Current PM suggestions are identical. Need varied savings amounts, asset types, reasons, and frequency changes to look credible. |
| 4 | **Empty state / onboarding** | New real user sees "Connect your CMMS" prompt instead of someone else's data. |

---

## Phase 3 — MaintainX Integration (Current Priority)

**Positioning:** *"Keep using MaintainX for work orders. Connect TrueSignal to get failure predictions, PM optimization, and KPI intelligence your MaintainX dashboard can't show you."*

### Build Order
| # | Task | Detail |
|---|------|--------|
| 1 | **Settings page** | Where customer enters their MaintainX API key after signup |
| 2 | **MaintainX adapter** | Pulls `/workorders` + `/assets` → maps to internal work_orders schema |
| 3 | **Sync worker** | Daily job: fetch new WOs → run pipeline → update dashboard |
| 4 | **Multi-tenant scoping** | Scope all DB queries by org_id so each customer sees only their data |

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

### Notifications
| # | Task | Detail |
|---|------|--------|
| 4 | **Email alerts** | Configurable triggers: new CRITICAL asset, weekly fleet digest, PM suggestion accepted. Uses Resend. |

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
