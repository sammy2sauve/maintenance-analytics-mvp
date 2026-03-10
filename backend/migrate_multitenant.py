"""
Migration script: single-tenant → multi-tenant (Org → Location → User).

Creates orgs, locations, user_location_access tables.
Moves mx_api_key_enc/salt/nonce from users to locations.
Adds location_id to data tables.
Migrates existing users to a default org + location.

Safe to re-run — uses IF NOT EXISTS / try-except for idempotency.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. Create new tables ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orgs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id          INTEGER NOT NULL REFERENCES orgs(id),
            name            TEXT NOT NULL,
            mx_api_key_enc  BLOB,
            mx_api_key_salt BLOB,
            mx_api_key_nonce BLOB,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_location_access (
            user_id     INTEGER NOT NULL REFERENCES users(id),
            location_id INTEGER NOT NULL REFERENCES locations(id),
            role        TEXT NOT NULL DEFAULT 'viewer',
            PRIMARY KEY (user_id, location_id)
        )
    """)

    # ── 2. Add org_id + role to users (if not present) ──────────────────────
    existing_cols = {r["name"] for r in cur.execute("PRAGMA table_info(users)").fetchall()}

    for col, typedef in [("org_id", "INTEGER"), ("role", "TEXT DEFAULT 'member'")]:
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
            print(f"  Added users.{col}")

    # ── 3. Add location_id to data tables ───────────────────────────────────
    data_tables = [
        "asset_failure_predictions",
        "pm_optimization_suggestions",
        "maintenance_insights",
        "work_orders",
    ]
    for table in data_tables:
        cols = {r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
        if "location_id" not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN location_id INTEGER")
            print(f"  Added {table}.location_id")

    # ── 4. Migrate existing users → default org + location ──────────────────
    users = cur.execute("SELECT * FROM users").fetchall()

    for user in users:
        user = dict(user)
        if user.get("org_id"):
            continue  # already migrated

        # Create a default org for this user
        cur.execute(
            "INSERT INTO orgs (name) VALUES (?)",
            (f"{user['name']}'s Organization",),
        )
        org_id = cur.lastrowid

        # Create a default location, moving API key from user
        cur.execute(
            """INSERT INTO locations (org_id, name, mx_api_key_enc, mx_api_key_salt, mx_api_key_nonce)
               VALUES (?, ?, ?, ?, ?)""",
            (
                org_id,
                "Default Location",
                user.get("api_key_enc"),
                user.get("api_key_salt"),
                user.get("api_key_nonce"),
            ),
        )
        location_id = cur.lastrowid

        # Update user with org_id and admin role
        cur.execute(
            "UPDATE users SET org_id = ?, role = 'admin' WHERE id = ?",
            (org_id, user["id"]),
        )

        # Grant admin access to the location
        cur.execute(
            "INSERT OR IGNORE INTO user_location_access (user_id, location_id, role) VALUES (?, ?, 'admin')",
            (user["id"], location_id),
        )

        # Assign existing data rows to this location
        for table in data_tables:
            cur.execute(
                f"UPDATE {table} SET location_id = ? WHERE location_id IS NULL",
                (location_id,),
            )

        print(f"  Migrated user {user['email']} -> org={org_id}, location={location_id}")

    conn.commit()
    conn.close()
    print("Multi-tenant migration complete.")


if __name__ == "__main__":
    migrate()
