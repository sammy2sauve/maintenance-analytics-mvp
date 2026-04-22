# TrueSignal — Pre-Launch Task List

Priority order. Each item is self-contained and can be done in a single session.

---

## 🔴 Critical (must ship before any real users)

### 1. SECRET_KEY → env var
Move hardcoded `SECRET_KEY` in `backend/auth.py` to an environment variable.
Read via `os.getenv("SECRET_KEY")` with a startup assertion if missing.
Add to Railway env vars and local `.env`.

### 2. Email verification enforced
On login, if `email_verified = false` → return 403 + redirect to `/verify-email` screen.
Block all data API routes (`/predictions`, `/work-orders`, `/settings`, etc.) for unverified users via FastAPI dependency.
Frontend: route guard in `AuthContext` — if `!emailVerified`, redirect to a "Check your email" page.

### 3. Terms & Privacy pages
- `/terms` — Terms of Service page
- `/privacy` — Privacy Policy page
- Link both from signup footer and pricing page footer
- Required by Stripe before account approval

### 4. Vercel + Railway deployment
- Frontend → Vercel. Set `VITE_API_URL` env var pointing to Railway backend URL.
- Backend → Railway. Set all env vars: `DATABASE_URL`, `SECRET_KEY`, `RESEND_API_KEY`, `TRUESIGNAL_MASTER_KEY`, `APP_URL`.
- Custom domain via Vercel DNS.
- Test all API routes end-to-end in production environment.

### 5. Stripe integration
- Wire `POST /billing/upgrade` to Stripe Checkout (subscription, not one-time).
- On checkout success webhook: set `plan='pro'`, `tier='pro'`, `stripe_customer_id`, `stripe_subscription_id`, clear `trial_ends_at`.
- On cancellation/payment failure webhook: downgrade org to `plan='expired'`.
- Store `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` in env vars.

---

## 🟠 High (ship within first week)

### 6. Settings page — billing & plan UI
- Show current plan (Free Trial / Starter / Pro / Enterprise) with trial countdown if applicable.
- Upgrade button → Stripe Checkout.
- If trial expired or plan lapsed: show locked/gated view matching demo screens.
- Cancel subscription option (calls Stripe API, sets plan to 'cancelled').

### 7. Trial/plan enforcement
- On every authenticated request, check `trial_ends_at` and `plan` on the org.
- If trial expired and no active paid plan: return 402 on data endpoints.
- Frontend: on 402, show upgrade modal / gated view instead of dashboard.

### 8. Cloudflare setup (after deploy)
- Point custom domain through Cloudflare (Railway/Vercel become origin servers).
- Enable DDoS protection, Bot Fight Mode, HTTPS enforcement.
- Add rate limiting rule on `/auth/*` (login, signup, forgot-password): max 10 req/min per IP.
- Enable WAF managed rules (free tier).

---

## 🟡 Medium (polish before marketing)

### 9. DB hardening
- Add `UNIQUE(title, location_id)` to `maintenance_insights` to prevent duplicate insight rows.
- Create read-only Neon role for analytics queries.
- Add FastAPI rate limiting middleware (slowapi) as second layer behind Cloudflare.
- Drop stale columns `api_key_enc/salt/nonce` from `users` table.

### 10. API-layer rate limiting
- Add `slowapi` to FastAPI. Limit `/auth/login` to 5/min, general API to 100/min per user.

### 11. Promo codes admin UI
- Simple `/admin/promo-codes` page (owner-only) to create/view/deactivate promo codes.
- Table view of existing codes with redemption count.

### 12. Daily sync worker
- Scheduled job (Railway cron or APScheduler) to run FaciliWorks sync once per day per location that has an API key.

### 13. Insight deduplication
- Add `UNIQUE(title, location_id)` constraint to `maintenance_insights`.
- Update `pipeline.py` to use `INSERT ... ON CONFLICT DO NOTHING`.

---

## 🔵 Backlog

- Landing page: app screenshot carousel / live demo account preview
- Page load speed: parallel fetches, React Query caching, Neon pooled endpoint
- AFP server-side dedup: ensure all endpoints filter to MAX(prediction_date) per asset
- Scheduled reports (job worker + schedule management UI)
- SOC 2 / HIPAA readiness assessment (when enterprise customers require it)
- Multi-location UI (currently shows locations[0] only)
