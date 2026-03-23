"""
Migration script: add tiers, seat limits, and invite_codes table.

Adds tier + seat_limit columns to orgs.
Creates invite_codes table with indexes.
Promotes sole-org users to 'owner' in user_location_access.

Safe to re-run — uses IF NOT EXISTS / try-except for idempotency.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. Add tier + seat_limit to orgs ──────────────────────────────────
    for col, typedef in [("tier", "TEXT NOT NULL DEFAULT 'starter'"), ("seat_limit", "INTEGER DEFAULT 3")]:
        try:
            cur.execute(f"ALTER TABLE orgs ADD COLUMN {col} {typedef}")
            print(f"  Added orgs.{col}")
        except Exception:
            print(f"  orgs.{col} already exists, skipping")

    # ── 2. Create invite_codes table ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL UNIQUE,
            org_id      INTEGER NOT NULL REFERENCES orgs(id),
            location_id INTEGER NOT NULL REFERENCES locations(id),
            role        TEXT NOT NULL DEFAULT 'viewer',
            created_by  INTEGER NOT NULL REFERENCES users(id),
            used_by     INTEGER REFERENCES users(id),
            expires_at  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    print("  invite_codes table ensured")

    # ── 3. Create indexes ─────────────────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_org ON invite_codes(org_id)")
    print("  invite_codes indexes ensured")

    # ── 4. Promote sole-org users to 'owner' ──────────────────────────────
    cur.execute("""
        UPDATE user_location_access SET role = 'owner'
        WHERE (user_id, location_id) IN (
            SELECT ula.user_id, ula.location_id
            FROM user_location_access ula
            JOIN locations l ON l.id = ula.location_id
            JOIN (SELECT l2.org_id FROM user_location_access ula2
                  JOIN locations l2 ON l2.id = ula2.location_id
                  GROUP BY l2.org_id HAVING COUNT(*) = 1) sole
              ON sole.org_id = l.org_id
        )
    """)
    promoted = cur.rowcount
    print(f"  Promoted {promoted} sole-org user(s) to 'owner'")

    conn.commit()
    conn.close()
    print("Tiers + invites migration complete.")


if __name__ == "__main__":
    migrate()
