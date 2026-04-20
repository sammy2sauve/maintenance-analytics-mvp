"""
Migration: add billing columns to orgs table.
Idempotent — safe to run multiple times.
"""
from dotenv import load_dotenv
load_dotenv()

from .neon import get_conn


def migrate():
    conn = get_conn()
    cur = conn.cursor()

    # Add plan column (trial / pro / enterprise)
    cur.execute("""
        ALTER TABLE orgs
        ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'trial'
    """)

    # Add trial expiry
    cur.execute("""
        ALTER TABLE orgs
        ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ
    """)

    # Stripe integration columns (populated when Stripe is wired up)
    cur.execute("""
        ALTER TABLE orgs
        ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT
    """)
    cur.execute("""
        ALTER TABLE orgs
        ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT
    """)

    # Extra seats purchased on Pro (beyond the 3 included)
    cur.execute("""
        ALTER TABLE orgs
        ADD COLUMN IF NOT EXISTS extra_seats INTEGER NOT NULL DEFAULT 0
    """)

    # Backfill: existing orgs get a trial that already expired
    # (they're the demo/dev accounts — won't be affected by trial gating)
    cur.execute("""
        UPDATE orgs
        SET plan = 'trial',
            trial_ends_at = NOW() - INTERVAL '1 day'
        WHERE trial_ends_at IS NULL
    """)

    conn.commit()
    conn.close()
    print("Billing migration complete.")


if __name__ == "__main__":
    migrate()
