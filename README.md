# TrueSignal — Predictive Maintenance Intelligence

Maintenance teams lose hours every week chasing false alarms and reacting to unexpected failures. TrueSignal connects to FaciliWorks, analyzes work order history, and tells you which assets are going to fail — before they do.

**[Live demo →](https://truesignalapp.com)**

---

## The Problem

Most CMMS tools are good at recording what happened. None of them tell you what's about to happen. Maintenance managers run on gut feel and reactive schedules, missing early failure signals buried in thousands of work orders.

## What TrueSignal Does

- **Failure predictions** — Every asset scored CRITICAL / HIGH / MEDIUM / LOW with estimated days to failure
- **PM optimization** — Identifies over- and under-maintained assets, generates adjusted PM schedules
- **KPI intelligence** — Strips out rushed completions and data quality distortions to show you real metrics
- **AI insights** — Plain-language summaries of what's happening across your fleet

---

## Live Demo

Click **Try the Demo** at [truesignalapp.com](https://truesignalapp.com). No sign-up required — loads a pre-seeded hospital facility (Meridian Medical Center, 29 assets).

To test the FaciliWorks connection yourself, create a free account and enter these credentials in Settings:

| Field | Value |
|---|---|
| Base URL | `https://maintenance-analytics-mvp.onrender.com/mock-fw` |
| API Key | `demo-key` |

This connects to a mock FaciliWorks server that returns realistic work order and asset data, then runs the full prediction pipeline.

**[FaciliWorks API documentation →](https://faciliworks.com/api-documentation)**

---

## Stack

| Layer | Tech | Why |
|---|---|---|
| Frontend | React + Vite + Tailwind + Recharts | Fast iteration, no runtime overhead |
| Backend | FastAPI (Python) | Async-friendly, great for data-heavy endpoints |
| Database | Neon PostgreSQL | Serverless Postgres with connection pooling — free tier handles demo traffic |
| Auth | JWT (python-jose) | Stateless, works across free-tier deployments that spin down |
| Deployment | Vercel (frontend) + Render (backend) | Both have free tiers that survive a portfolio project's traffic |

---

## Architecture

```
Browser (Vercel)
    ↓ HTTPS
FastAPI (Render)
    ├── /auth         JWT auth, demo login
    ├── /predictions  Failure predictions + PM suggestions
    ├── /kpis         Daily/weekly/monthly KPI aggregates
    ├── /settings     FaciliWorks credential storage (encrypted at rest)
    ├── /reports      PDF/CSV export
    └── /mock-fw      Mock FaciliWorks API for demo/testing
    ↓
Neon PostgreSQL
    ├── orgs / locations / users (multi-tenant)
    ├── asset_failure_predictions
    ├── pm_optimization_suggestions
    └── work_orders / kpi_daily / kpi_weekly
```

**Multi-tenant:** Every data row is scoped to a `location_id`. One database, fully isolated tenants.

**Demo mode:** `/auth/demo` issues a short-lived JWT for a read-only pre-seeded location. No credentials required.

---

## Key Technical Decisions

**Why encrypt API keys at rest?** FaciliWorks credentials give read access to a customer's entire CMMS. Storing them in plaintext in a shared Postgres instance would be a single point of compromise. Keys are AES-256 encrypted before write, decrypted only in the sync worker.

**Why a separate prediction pipeline instead of in-request computation?** Failure scoring runs across months of work order history per asset. Running that synchronously on every page load would make the app unusable. Instead, predictions are precomputed on sync and served as simple table reads.

**Why mock FaciliWorks?** Testing against a live CMMS account is slow and risky (real work orders could be modified). The mock server returns deterministic data in the exact FaciliWorks API format, letting the full adapter→pipeline→predictions stack run in CI with no external dependencies.

---

## Local Setup

```bash
# 1. Clone and create .env
cp .env.example .env
# Fill in DATABASE_URL (Postgres), SECRET_KEY (any random string)

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn backend.api:app --reload
# → http://localhost:8000

# 3. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173

# 4. (Optional) Mock FaciliWorks server
uvicorn backend.mock_faciliworks:app --port 8001 --reload
# Then in Settings: Base URL = http://localhost:8001, API Key = any-string
```

---

## What I'd Do Next

- **Rate limiting** — Add slowapi middleware to protect the free-tier backend from traffic spikes
- **Webhook sync** — Replace manual sync button with FaciliWorks webhook push for real-time predictions
- **More CMMS adapters** — MaintainX and Limble share similar work order schemas; the adapter pattern is already in place
- **Anomaly detection** — Replace heuristic failure scoring with a lightweight LSTM trained on historical breakdown patterns
