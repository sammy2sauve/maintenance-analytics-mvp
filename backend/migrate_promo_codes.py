"""
Migration: create promo_codes table.
Idempotent — safe to run multiple times.
"""
from dotenv import load_dotenv
load_dotenv()

from .neon import get_conn


def migrate():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id              SERIAL PRIMARY KEY,
            code            TEXT NOT NULL UNIQUE,
            discount_type   TEXT NOT NULL CHECK (discount_type IN ('trial_days', 'free_pro')),
            discount_value  INTEGER NOT NULL,   -- days
            max_uses        INTEGER,            -- NULL = unlimited
            times_used      INTEGER NOT NULL DEFAULT 0,
            expires_at      TIMESTAMPTZ,
            active          BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    conn.close()
    print("Promo codes migration complete.")


if __name__ == "__main__":
    migrate()
