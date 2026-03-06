# TrueSignal — Maintenance Analytics Platform

Predictive maintenance intelligence for industrial and facilities teams. TrueSignal connects to your CMMS (MaintNext), analyzes work order history and asset data, and surfaces failure predictions, PM optimization opportunities, and KPI trends — all in a real-time dashboard.

---

## What It Does

**Overview** — Fleet-level health score, risk distribution, key KPIs, and AI-generated insights. Filterable by time range (7d / 30d / 90d / All).

**Asset Health** — Every monitored asset ranked by failure risk (CRITICAL / HIGH / MEDIUM / LOW). Glowing risk rings show fleet breakdown at a glance. Urgency histogram shows how many assets are predicted to fail in each time window. Export to CSV.

**Cost Savings** — PM optimization recommendations ranked by estimated annual savings. Status rings track which suggestions have been Pending → Accepted → Implemented (synced via CMMS webhooks). Cumulative savings waterfall shows total value unlocked as PMs are applied. Export to CSV.

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Router |
| Backend | Python, FastAPI |
| Database | SQLite (MVP) → Postgres (production) |
| Data pipeline | Custom Python — ingests MaintNext exports, calculates KPIs, runs predictive models |

---

## Running Locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload
# API at http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

---

## Roadmap

See [LAUNCH_ROADMAP.md](./LAUNCH_ROADMAP.md) for the full path to commercial launch.

Next up: logo, asset type encoding, auth, MaintNext live integration, Postgres migration, deployment.
