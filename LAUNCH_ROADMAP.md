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

These items must be done before any real customer uses the product.

| # | Task | Detail |
|---|------|--------|
| 1 | **Reset password** | Forgot password flow — email with reset link. Needs domain + email service (Resend) first. |
| 2 | **Demo account + demo data** | A locked `demo@truesignal.io` account that shows realistic synthetic data. Used for sales calls and prospects who want to self-explore without connecting their CMMS. |
| 3 | **Realistic cost savings data** | Current PM suggestions are all identical ($920, same reason, same freq). Need varied savings amounts, different asset types, different reasons, different frequency changes to look credible. |
| 4 | **Empty state / onboarding** | New real user (non-demo) sees "Connect your CMMS" prompt instead of someone else's data. |

---

## Phase 3 — MaintainX Integration (Current Priority)

**Why MaintainX first:** #1 rated CMMS on G2, fastest growing in mid-market. Top user complaint is poor analytics (57 G2 mentions) — exactly what TrueSignal solves. TrueSignal is not competing with MaintainX, it's the intelligence layer on top of it.

**Positioning:** *"Keep using MaintainX for work orders. Connect TrueSignal to get failure predictions, PM optimization, and KPI intelligence your MaintainX dashboard can't show you."*

### Integration Architecture
```
Customer signs up on TrueSignal
  → pastes MaintainX API key (one-time, ~2 min setup)
  → TrueSignal pulls work orders + assets on daily schedule
  → pipeline runs automatically
  → dashboard populates with their real data
```

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
| 4 | **Billing** | Stripe — per-seat or per-asset pricing |

---

## Phase 5 — Growth

| # | Task | Detail |
|---|------|--------|
| 1 | **CMMS webhook for PM status** | MaintainX pushes Accepted/Implemented back when PMs are actioned |
| 2 | **Additional CMMS adapters** | Limble, UpKeep, Fiix — same pattern as MaintainX |
| 3 | **Email alerts** | Weekly digest: "3 new CRITICAL assets this week" |
| 4 | **PDF report export** | One-click monthly report for customer's leadership |
| 5 | **OAuth for MaintainX** | Replace API key paste with "Connect MaintainX" button |

---

## Shortest Path to First Paying Customer

```
Realistic demo data + demo account
  → MaintainX integration (API key, daily sync)
  → Multi-tenant data scoping
  → Deploy to hosted URL
  → Legal (LLC + MSA)
  → Reset password (needs domain + email service)
  → First customer
```
