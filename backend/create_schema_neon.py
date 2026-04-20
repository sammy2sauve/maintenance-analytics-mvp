"""
Create all TrueSignal tables in the Neon PostgreSQL database.

Safe to re-run — all statements use IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.

Usage:
    python -m backend.create_schema_neon
"""

from .neon import get_db


SCHEMA = """
-- ── Multi-tenant core ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orgs (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    tier       TEXT NOT NULL DEFAULT 'starter',
    seat_limit INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS locations (
    id               SERIAL PRIMARY KEY,
    org_id           INTEGER NOT NULL REFERENCES orgs(id),
    name             TEXT NOT NULL,
    mx_api_key_enc   BYTEA,
    mx_api_key_salt  BYTEA,
    mx_api_key_nonce BYTEA,
    cmms_base_url    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    org_id          INTEGER REFERENCES orgs(id),
    email           TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role            TEXT DEFAULT 'member',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_location_access (
    user_id     INTEGER NOT NULL REFERENCES users(id),
    location_id INTEGER NOT NULL REFERENCES locations(id),
    role        TEXT NOT NULL DEFAULT 'viewer',
    PRIMARY KEY (user_id, location_id)
);

CREATE TABLE IF NOT EXISTS invite_codes (
    id          SERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    org_id      INTEGER NOT NULL REFERENCES orgs(id),
    location_id INTEGER NOT NULL REFERENCES locations(id),
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_by  INTEGER NOT NULL REFERENCES users(id),
    used_by     INTEGER REFERENCES users(id),
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Work orders (operational data synced from CMMS) ────────────────────────

CREATE TABLE IF NOT EXISTS work_orders (
    work_order_id         BIGINT PRIMARY KEY,
    asset_id              TEXT,
    site                  TEXT,
    type                  TEXT,
    status                TEXT,
    technician            TEXT,
    creation_date         DATE,
    scheduled_start       DATE,
    start_date            DATE,
    completion_date       DATE,
    labor_hours_scheduled REAL,
    labor_hours_actual    REAL,
    downtime_hours        REAL,
    reactive_followup     INTEGER,
    priority              TEXT,
    due_date              DATE,
    location_id           INTEGER REFERENCES locations(id)
);

CREATE INDEX IF NOT EXISTS idx_wo_asset     ON work_orders(asset_id);
CREATE INDEX IF NOT EXISTS idx_wo_location  ON work_orders(location_id);
CREATE INDEX IF NOT EXISTS idx_wo_type      ON work_orders(type);
CREATE INDEX IF NOT EXISTS idx_wo_status    ON work_orders(status);

-- ── KPI storage ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS daily_kpis (
    id               SERIAL PRIMARY KEY,
    period_date      DATE NOT NULL,
    kpi_name         TEXT NOT NULL,
    raw_value        REAL,
    truesignal_value REAL,
    distortion_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    explanation_text TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_date, kpi_name)
);

CREATE TABLE IF NOT EXISTS weekly_kpis (
    id               SERIAL PRIMARY KEY,
    period_week      TEXT NOT NULL,
    kpi_name         TEXT NOT NULL,
    raw_value        REAL,
    truesignal_value REAL,
    distortion_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    explanation_text TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_week, kpi_name)
);

CREATE TABLE IF NOT EXISTS monthly_kpis (
    id               SERIAL PRIMARY KEY,
    period_month     TEXT NOT NULL,
    kpi_name         TEXT NOT NULL,
    raw_value        REAL,
    truesignal_value REAL,
    distortion_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    explanation_text TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_month, kpi_name)
);

CREATE INDEX IF NOT EXISTS idx_daily_kpis_period   ON daily_kpis(period_date);
CREATE INDEX IF NOT EXISTS idx_daily_kpis_name     ON daily_kpis(kpi_name);
CREATE INDEX IF NOT EXISTS idx_weekly_kpis_period  ON weekly_kpis(period_week);
CREATE INDEX IF NOT EXISTS idx_weekly_kpis_name    ON weekly_kpis(kpi_name);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_period ON monthly_kpis(period_month);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_name   ON monthly_kpis(kpi_name);

-- ── Predictive analytics storage ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS asset_failure_predictions (
    id                        SERIAL PRIMARY KEY,
    asset_id                  TEXT NOT NULL,
    prediction_date           DATE NOT NULL,
    failure_probability       REAL NOT NULL,
    days_to_predicted_failure INTEGER,
    confidence_score          REAL,
    mtbf_days                 REAL,
    days_since_last_pm        INTEGER,
    reactive_work_count_90d   INTEGER,
    risk_level                TEXT,
    recommendation            TEXT,
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    location_id               INTEGER REFERENCES locations(id),
    UNIQUE(asset_id, prediction_date, location_id)
);

CREATE TABLE IF NOT EXISTS pm_optimization_suggestions (
    id                          SERIAL PRIMARY KEY,
    asset_id                    TEXT NOT NULL,
    current_pm_frequency_days   INTEGER,
    suggested_pm_frequency_days INTEGER,
    reason                      TEXT,
    estimated_cost_savings      REAL,
    estimated_risk_change       REAL,
    confidence_score            REAL,
    reactive_work_after_pm_count INTEGER,
    suggestion_date             DATE NOT NULL,
    status                      TEXT DEFAULT 'pending',
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    location_id                 INTEGER REFERENCES locations(id),
    UNIQUE(asset_id, location_id)
);

CREATE TABLE IF NOT EXISTS maintenance_insights (
    id               SERIAL PRIMARY KEY,
    insight_type     TEXT NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT,
    confidence_score REAL,
    impact_level     TEXT,
    affected_assets  TEXT,
    metric_value     REAL,
    insight_date     DATE NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    location_id      INTEGER REFERENCES locations(id),
    UNIQUE(insight_type, title, location_id)
);

CREATE INDEX IF NOT EXISTS idx_afp_asset    ON asset_failure_predictions(asset_id);
CREATE INDEX IF NOT EXISTS idx_afp_date     ON asset_failure_predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_afp_risk     ON asset_failure_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_pms_asset    ON pm_optimization_suggestions(asset_id);
CREATE INDEX IF NOT EXISTS idx_mi_type      ON maintenance_insights(insight_type);

-- ── Email verification (added post-launch) ──────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified           BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token TEXT;

-- ── Password reset ───────────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token      TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMPTZ;

-- ── Alert rules ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alert_rules (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    rule_key      TEXT NOT NULL,
    threshold     REAL,
    channel       TEXT NOT NULL DEFAULT 'Email',
    frequency     TEXT NOT NULL DEFAULT 'Immediately',
    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    last_fired_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, location_id, rule_key)
);
"""


def create_schema():
    print("Creating TrueSignal schema in Neon...")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(SCHEMA)
    print("Schema created successfully.")


if __name__ == "__main__":
    create_schema()
