# TrueSignal — Launch Roadmap

> Last updated: March 2026

---

## Where We Are

The core product is built and demo-ready. Three-page analytics dashboard, predictive failure engine, PM optimization, live KPI tracking — all working against real synthetic data shaped like MaintNext exports. The platform is ready to show a customer.

---

## Phase 1 — Close the MVP (Now)

Small data quality and polish items before any customer sees it.

| # | Task | Detail |
|---|------|--------|
| 1 | **Logo / branding** | Replace text subtitle in header with logo SVG |
| 2 | **Asset type encoding** | Rename `ASSET-XXX` → `PUMP-XXX`, `HVAC-XXX`, etc. in pipeline — makes Asset Health page readable by type |
| 3 | **`MAINT-XXX` / `ASSET-XXX` ID mismatch** | PM optimization and failure predictions use different ID schemes — backend join needed so Cost Savings references real assets |

---

## Phase 2 — Customer Demo Ready

| # | Task | Detail |
|---|------|--------|
| 4 | **Auth / Login** | Simple JWT login page — single-tenant for first customer. Blocks public exposure. |
| 5 | **MaintNext integration** | Pull live WO/PM data via MaintNext API instead of synthetic data. Biggest credibility leap. |
| 6 | **CMMS webhook for PM status** | Pending → Accepted → Implemented flow on Cost Savings page. Webhooks from MaintNext fire when a PM suggestion is actioned. |

---

## Phase 3 — Commercial Launch

| # | Task | Detail |
|---|------|--------|
| 7 | **Database migration** | Move off local SQLite → hosted Postgres (Railway, Supabase, or Neon). Required before any customer data touches it. |
| 8 | **Multi-tenant** | Scope all DB queries by `org_id`. One database, multiple customers isolated by row-level security. |
| 9 | **Deployment** | Frontend → Vercel or Netlify. Backend → Railway or Fly.io. Custom domain + SSL. |
| 10 | **Legal** | LLC formation, MSA/SaaS ToS template, Data Processing Agreement (DPA) for customer maintenance data. |

---

## Phase 4 — Growth

| # | Task | Detail |
|---|------|--------|
| 11 | **Email alerts** | "3 new CRITICAL assets this week" weekly digest — keeps customers engaged without logging in |
| 12 | **PDF report export** | One-click monthly report for customer's ops leadership |
| 13 | **Pricing / billing** | Stripe integration — seat-based or per-asset pricing |

---

## Shortest Path to First Paying Customer

```
Phase 1 (data quality + logo)
  → Auth (login wall)
  → MaintNext integration (real data)
  → Deploy to hosted URL
  → Legal (LLC + MSA)
  → First customer
```

Legal can run in parallel with everything. Everything in Phase 4 is post-revenue.

---

## Stack Reference

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, SQLite (→ Postgres) |
| Data pipeline | Custom Python — pulls from MaintNext, calculates KPIs, runs predictions |
| Hosting (target) | Vercel (frontend) + Railway (backend + DB) |
