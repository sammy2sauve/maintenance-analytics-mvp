# TrueSignal — Infrastructure & Launch Plan

> The cheapest path from SQLite MVP to production, with a two-person task split.

---

## 1. The Stack (Total: $0–7/month at launch)

### Database — Neon Postgres (Free Tier) ✅ RECOMMENDED

| | Detail |
|---|--------|
| **Why Neon** | Serverless Postgres, no container running 24/7. You only pay for compute you use. Supabase is overkill (you don't need their auth/storage layer — you already built your own). Railway burns through its $5 credit fast. |
| **Free tier** | 0.5 GB storage, 190 compute hours/month, 1 project, 10 branches |
| **What you get** | Full Postgres 16, connection pooling, database branching (test schema changes without touching prod), point-in-time restore |
| **When you outgrow it** | Launch plan starts at ~$19/month — you'll be well past first customers before that matters |
| **Connection** | Standard `postgres://` connection string — drop it into your FastAPI `DATABASE_URL` env var |

**Why not the others:**
- **Supabase** — Free tier is comparable but bundles auth, storage, edge functions you won't use. More moving parts = more things to debug. You already have JWT auth.
- **Railway** — Good for hosting your backend, but their Postgres eats your $5 credit alongside your app. Better to separate DB from compute.
- **PlanetScale** — MySQL only. You want Postgres.

---

### Domain — Cloudflare Registrar (~$10/year)

| | Detail |
|---|--------|
| **Why Cloudflare** | At-cost pricing (no markup on domain registration). A `.com` is ~$10/year. Also gives you free DNS, free SSL, DDoS protection, and CDN caching — all included at no extra cost. |
| **Setup** | Register `truesignal.io` or `truesignal.com` (check availability). Point DNS to your frontend (Vercel) and backend (Railway/Fly). |
| **Email routing** | Cloudflare Email Routing is free — forward `hello@truesignal.io` to your personal Gmail. No need to pay for Google Workspace yet. |

**Why not the others:**
- **Namecheap/GoDaddy** — Markup pricing, upsells, worse DNS. Cloudflare is just cheaper and better.
- **Google Domains** — Shut down, migrated to Squarespace. Skip.

---

### Payments — Stripe

| | Detail |
|---|--------|
| **Cost** | $0/month. 2.9% + $0.30 per transaction — you only pay when you get paid. |
| **What to use** | Stripe Checkout (hosted payment page) or Stripe Billing (subscriptions). For MVP, use Checkout — it's a single redirect, no custom payment UI needed. |
| **Setup** | Create Stripe account → add products/prices → generate a Checkout Session from your FastAPI backend → redirect user to Stripe's hosted page → webhook confirms payment → flip `is_active` in your DB. |
| **Alternatives considered** | Lemon Squeezy (handles sales tax for you, slightly higher fees), Paddle (same). Stripe is the standard — biggest ecosystem, best docs, most flexibility. |

---

### Deployment (Free)

| Service | Use | Cost |
|---------|-----|------|
| **Vercel** | React frontend | Free (hobby tier) |
| **Railway** | FastAPI backend | Free ($5 credit/month) |
| **Neon** | Postgres database | Free tier |
| **Resend** | Transactional email (password reset, alerts) | Free (100 emails/day) |
| **Cloudflare** | Domain + DNS + SSL + CDN | ~$10/year for the domain |

**Total monthly cost: $0** until you exceed free tiers (which won't happen until you have paying customers).

---

## 2. Getting Your Brother Set Up

### His machine setup (30 minutes)

```
1. Install Git, Node.js, Python 3.11+
2. You add him as collaborator on GitHub repo
3. He clones: git clone https://github.com/novashadeprod/truesignal.git
4. Backend:  cd backend && pip install -r requirements.txt
5. Frontend: cd frontend && npm install
6. You send him .env values over Signal/iMessage (not Slack/Discord)
7. He runs create_db.py to seed local SQLite for dev
8. He runs both servers — if he sees the dashboard, he's good
```

### Workflow rules (agree on these before he writes a line of code)

- `main` branch is always deployable — never commit directly to it
- Feature branches named: `feat/description`, `fix/description`
- Pull requests for everything — even small changes. Review each other's work.
- Pull from `main` every morning before starting work
- Don't touch the same files at the same time — the task split below is designed to avoid this

---

## 3. Task Split — You vs. Your Brother

### You (Backend / Data Engineering)

| # | Task | Detail |
|---|------|--------|
| 1 | **Postgres migration** | Set up Neon project. Rewrite SQLAlchemy models for new schema. Write migration script (SQLite → Postgres). Update `DATABASE_URL` config. |
| 2 | **New data schema** | Redesign tables to be CMMS-agnostic so the adapter pattern works for FaciliWorks, MaintainX, and future platforms. See schema proposal below. |
| 3 | **FaciliWorks adapter** | New adapter that pulls from FaciliWorks REST API → normalized schema. Same pattern as MaintainX adapter. |
| 4 | **Reset password backend** | Token generation, Resend email integration, `/auth/reset-password` and `/auth/confirm-reset` endpoints. |
| 5 | **Stripe integration** | Backend webhook handler, subscription status check middleware, product/price setup. |

### Your Brother (Frontend / UI Polish)

| # | Task | Detail |
|---|------|--------|
| 1 | **UI polish pass** | Spacing, responsiveness, loading states, error states, mobile viewport fixes. |
| 2 | **PDF report redesign** | Fix the report generation — layout, styling, content density. This is self-contained React + PDF logic, minimal backend coupling. |
| 3 | **Demo account UI** | Read-only mode, "You're viewing demo data" banner, lock out settings/sync for demo users. |
| 4 | **Reset password frontend** | Forgot password form, reset confirmation page, success/error states. Wires up to your backend endpoints. |
| 5 | **Stripe Checkout frontend** | Pricing page, "Subscribe" button that redirects to Stripe Checkout, post-payment success/cancel pages. |

### Shared / Do Together

| Task | Why together |
|------|-------------|
| **Agree on new schema** | 30-min whiteboard session before anyone writes code. He needs to know what the API responses look like so he can build components against them. |
| **API contract for new endpoints** | You define the request/response shape, he builds the frontend against it. Write it down in a shared doc or in the repo as a markdown file. |
| **Testing before deploy** | Both of you test the full flow end-to-end before merging to main. |

---

## 4. Proposed CMMS-Agnostic Schema (Postgres)

This replaces your current SQLite tables. The key idea: **every table is CMMS-agnostic**. The adapter translates platform-specific data into this universal shape.

```sql
-- Multi-tenant hierarchy
organizations (
    id, name, created_at
)

locations (
    id, org_id → organizations, name,
    cmms_platform,          -- 'faciliworks' | 'maintainx' | 'limble'
    cmms_api_key_encrypted,
    cmms_base_url,          -- FaciliWorks needs this (self-hosted instances)
    last_synced_at,
    created_at
)

users (
    id, org_id → organizations, location_id → locations,
    email, password_hash, role,  -- 'admin' | 'viewer'
    is_demo, is_active,
    reset_token, reset_token_expires_at,
    stripe_customer_id, subscription_status,
    created_at
)

-- Core normalized data (all CMMS data lands here)
assets (
    id, location_id → locations,
    cmms_asset_id,          -- original ID in FaciliWorks/MaintainX
    name, asset_type,       -- 'HVAC' | 'Pump' | 'Conveyor' etc.
    category, model, manufacturer,
    install_date, status,   -- 'active' | 'inactive' | 'decommissioned'
    parent_asset_id,        -- FaciliWorks has asset hierarchy
    metadata JSONB,         -- catch-all for platform-specific fields
    created_at, updated_at
)

work_orders (
    id, location_id → locations,
    asset_id → assets,
    cmms_wo_id,
    title, description,
    wo_type,                -- 'corrective' | 'preventive' | 'inspection'
    priority,               -- 'critical' | 'high' | 'medium' | 'low'
    status,                 -- 'open' | 'in_progress' | 'completed' | 'cancelled'
    assigned_to,
    created_date, completed_date, due_date,
    labor_hours, parts_cost, total_cost,
    metadata JSONB,
    created_at, updated_at
)

-- TrueSignal's analytics outputs
predictions (
    id, location_id → locations,
    asset_id → assets,
    risk_score, risk_level,  -- 'critical' | 'high' | 'medium' | 'low'
    predicted_failure_date,
    failure_mode, confidence,
    insights JSONB,
    created_at
)

pm_suggestions (
    id, location_id → locations,
    asset_id → assets,
    suggestion_text,
    estimated_savings,
    status,                 -- 'pending' | 'accepted' | 'implemented' | 'dismissed'
    implemented_date,
    matched_wo_id → work_orders,
    created_at, updated_at
)

kpi_snapshots (
    id, location_id → locations,
    period,                 -- 'daily' | 'weekly' | 'monthly'
    period_start, period_end,
    mtbf, mttr, availability,
    pm_compliance, backlog_count,
    fleet_health_score,
    data JSONB,             -- full KPI breakdown
    created_at
)

sync_logs (
    id, location_id → locations,
    started_at, completed_at,
    records_fetched, records_processed,
    status,                 -- 'success' | 'partial' | 'failed'
    error_message
)
```

### Key design decisions:
- **`cmms_platform` on locations**, not globally — one org could have different sites using different CMMS
- **`cmms_base_url`** — FaciliWorks supports self-hosted/on-prem, so the API URL varies per customer (unlike MaintainX which is always `api.getmaintainx.com`)
- **`metadata JSONB`** — catch-all for platform-specific fields you don't want to lose but don't need columns for (calibration data, test points, compliance fields from FaciliWorks)
- **`parent_asset_id`** — FaciliWorks has asset hierarchy (systems → subsystems → components). MaintainX doesn't, but the column is nullable so it's fine.

---

## 5. FaciliWorks Adapter — What We Know

From the Swagger docs at `api.staging.faciliworks.com` and the Makini integration mapping, FaciliWorks exposes:

| FaciliWorks Entity | Maps to TrueSignal Table |
|---|---|
| Assets (with hierarchy) | `assets` (with `parent_asset_id`) |
| Work Orders (corrective maintenance) | `work_orders` (wo_type = 'corrective') |
| PM Schedules / PM Work Orders | `work_orders` (wo_type = 'preventive') |
| Service Requests | `work_orders` (wo_type = 'corrective', sourced from SR) |
| Asset Downtime | `metadata JSONB` on assets or separate table if needed |
| Parts/Inventory | Not needed for MVP — ignore |
| Sites/Locations | `locations` |
| Personnel | `assigned_to` field on work_orders |
| Calibration/Test Points | `metadata JSONB` — compliance data, store but don't analyze yet |

**⚠️ I still need to see the actual Swagger spec** to map field names precisely. Upload that JSON or send screenshots and I'll write the full adapter.

---

## 6. Execution Order

```
Week 1:
  You:  Set up Neon → design final schema → start migration script
  Bro:  Clone repo → get running locally → start UI polish pass

Week 2:
  You:  Finish migration → start FaciliWorks adapter
  Bro:  PDF report redesign → demo account UI

Week 3:
  You:  FaciliWorks adapter done → reset password backend → Stripe backend
  Bro:  Reset password frontend → Stripe checkout frontend

Week 4:
  Both: Integration testing → deploy to Vercel + Railway → custom domain
        → first demo to a real customer
```

---

## Quick Reference — Account Signups Needed

| Service | URL | What to do |
|---------|-----|------------|
| Neon | neon.tech | Sign up → create project → copy connection string |
| Cloudflare | cloudflare.com | Sign up → register domain → set up DNS |
| Vercel | vercel.com | Sign up with GitHub → import frontend repo |
| Railway | railway.app | Sign up with GitHub → deploy backend |
| Stripe | stripe.com | Sign up → create products/prices → get API keys |
| Resend | resend.com | Sign up → verify domain → get API key |
