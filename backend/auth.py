"""
Auth utilities -- password hashing, JWT, and multi-tenant user/org/location queries.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import sqlite3
import secrets

import bcrypt
from jose import JWTError, jwt

from .encryption import encrypt, decrypt

# -- Config -------------------------------------------------------------------
SECRET_KEY = "truesignal-dev-secret-change-in-prod"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

# -- DB setup -----------------------------------------------------------------

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_users_table():
    """Ensure all multi-tenant tables exist (idempotent)."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orgs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id          INTEGER REFERENCES orgs(id),
            email           TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            role            TEXT DEFAULT 'member',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_location_access (
            user_id     INTEGER NOT NULL REFERENCES users(id),
            location_id INTEGER NOT NULL REFERENCES locations(id),
            role        TEXT NOT NULL DEFAULT 'viewer',
            PRIMARY KEY (user_id, location_id)
        )
    """)
    conn.execute("""
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
    # Ensure columns exist for DBs that were created before multi-tenant
    for col, typedef in [("org_id", "INTEGER"), ("role", "TEXT DEFAULT 'member'")]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    for col, typedef in [("tier", "TEXT NOT NULL DEFAULT 'starter'"), ("seat_limit", "INTEGER DEFAULT 3")]:
        try:
            conn.execute(f"ALTER TABLE orgs ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.commit()
    conn.close()

# -- Password -----------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# -- JWT ----------------------------------------------------------------------

def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# -- User queries -------------------------------------------------------------

def get_user_by_email(email: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_locations(user_id: int) -> List[dict]:
    """Return all locations the user has access to."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT l.id, l.org_id, l.name,
               l.mx_api_key_enc IS NOT NULL as has_api_key,
               ula.role as access_role
        FROM locations l
        JOIN user_location_access ula ON ula.location_id = l.id
        WHERE ula.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -- API key storage (now on location, not user) ------------------------------

def save_location_api_key(location_id: int, plaintext_key: str) -> None:
    """Encrypt and store the location's MaintainX API key."""
    enc, salt, nonce = encrypt(plaintext_key)
    conn = _get_conn()
    conn.execute(
        "UPDATE locations SET mx_api_key_enc=?, mx_api_key_salt=?, mx_api_key_nonce=? WHERE id=?",
        (enc, salt, nonce, location_id)
    )
    conn.commit()
    conn.close()


def get_location_api_key(location_id: int) -> Optional[str]:
    """Decrypt and return the API key for a location. Server-side only."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT mx_api_key_enc, mx_api_key_salt, mx_api_key_nonce FROM locations WHERE id=?",
        (location_id,)
    ).fetchone()
    conn.close()
    if not row or row[0] is None:
        return None
    return decrypt(row[0], row[1], row[2])


def location_has_api_key(location_id: int) -> bool:
    """Check if a location has a stored API key. Safe for frontend."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT mx_api_key_enc FROM locations WHERE id=?", (location_id,)
    ).fetchone()
    conn.close()
    return bool(row and row[0] is not None)


def delete_location_api_key(location_id: int) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE locations SET mx_api_key_enc=NULL, mx_api_key_salt=NULL, mx_api_key_nonce=NULL WHERE id=?",
        (location_id,)
    )
    conn.commit()
    conn.close()


def user_can_access_location(user_id: int, location_id: int) -> bool:
    """Check if user has access to a given location."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM user_location_access WHERE user_id=? AND location_id=?",
        (user_id, location_id)
    ).fetchone()
    conn.close()
    return row is not None


# -- Backward-compat wrappers (used by api_settings until fully migrated) -----

def has_api_key(user_id: int) -> bool:
    """Check if user's first location has an API key."""
    locs = get_user_locations(user_id)
    if not locs:
        return False
    return bool(locs[0]["has_api_key"])


def save_user_api_key(user_id: int, plaintext_key: str) -> None:
    """Save API key to user's first location."""
    locs = get_user_locations(user_id)
    if not locs:
        return
    save_location_api_key(locs[0]["id"], plaintext_key)


def get_user_api_key(user_id: int) -> Optional[str]:
    """Get API key from user's first location."""
    locs = get_user_locations(user_id)
    if not locs:
        return None
    return get_location_api_key(locs[0]["id"])


def delete_user_api_key(user_id: int) -> None:
    """Delete API key from user's first location."""
    locs = get_user_locations(user_id)
    if not locs:
        return
    delete_location_api_key(locs[0]["id"])


# -- User creation (multi-tenant) --------------------------------------------

def create_user(name: str, email: str, password: str, org_name: str = None) -> dict:
    """
    Create a new user with org + location in one transaction.
    If org_name is not provided, defaults to "{name}'s Organization".
    """
    hashed = hash_password(password)
    if not org_name:
        org_name = f"{name}'s Organization"

    conn = _get_conn()
    try:
        # Create org
        cur = conn.execute("INSERT INTO orgs (name) VALUES (?)", (org_name,))
        org_id = cur.lastrowid

        # Create default location
        cur = conn.execute(
            "INSERT INTO locations (org_id, name) VALUES (?, ?)",
            (org_id, "Default Location")
        )
        location_id = cur.lastrowid

        # Create user
        cur = conn.execute(
            "INSERT INTO users (name, email, hashed_password, org_id, role) VALUES (?, ?, ?, ?, 'owner')",
            (name, email, hashed, org_id)
        )
        user_id = cur.lastrowid

        # Grant owner access to the location
        conn.execute(
            "INSERT INTO user_location_access (user_id, location_id, role) VALUES (?, ?, 'owner')",
            (user_id, location_id)
        )

        conn.commit()
    finally:
        conn.close()

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "org_id": org_id,
        "location_id": location_id,
    }


# -- Invite codes & team management ------------------------------------------

def create_user_shell(name: str, email: str, password: str) -> dict:
    """Create a bare user row with no org/location."""
    hashed = hash_password(password)
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, hashed_password, role) VALUES (?, ?, ?, 'member')",
            (name, email, hashed)
        )
        user_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return {"id": user_id, "name": name, "email": email}


def create_invite_code(org_id: int, location_id: int, created_by: int,
                       role: str = 'viewer', expires_days: int = 7) -> str:
    """Generate an invite code after checking seat limit."""
    conn = _get_conn()
    row = conn.execute("SELECT seat_limit FROM orgs WHERE id = ?", (org_id,)).fetchone()
    seat_limit = row[0] if row and row[0] is not None else None
    if seat_limit is not None:
        used = conn.execute("""
            SELECT COUNT(*) FROM user_location_access ula
            JOIN locations l ON l.id = ula.location_id
            WHERE l.org_id = ?
        """, (org_id,)).fetchone()[0]
        pending = conn.execute("""
            SELECT COUNT(*) FROM invite_codes
            WHERE org_id = ? AND used_by IS NULL
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (org_id,)).fetchone()[0]
        if used + pending >= seat_limit:
            conn.close()
            raise ValueError(f"Seat limit of {seat_limit} reached")
    expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat() if expires_days else None
    code = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO invite_codes (code, org_id, location_id, role, created_by, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (code, org_id, location_id, role, created_by, expires_at)
    )
    conn.commit()
    conn.close()
    return code


def validate_invite_code(code: str) -> Optional[dict]:
    """Return invite details or None if invalid/used/expired."""
    conn = _get_conn()
    row = conn.execute("""
        SELECT ic.id, ic.code, ic.org_id, ic.location_id, ic.role, ic.used_by, ic.expires_at,
               o.name as org_name, o.tier, o.seat_limit
        FROM invite_codes ic
        JOIN orgs o ON o.id = ic.org_id
        WHERE ic.code = ?
          AND ic.used_by IS NULL
          AND (ic.expires_at IS NULL OR ic.expires_at > datetime('now'))
    """, (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def accept_invite_code(code: str, user_id: int) -> None:
    """Mark code used, set user org_id, insert location access."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT org_id, location_id, role FROM invite_codes WHERE code = ? AND used_by IS NULL",
        (code,)
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError("Invite code not found or already used")
    org_id, location_id, role = row[0], row[1], row[2]
    conn.execute("UPDATE invite_codes SET used_by = ? WHERE code = ?", (user_id, code))
    conn.execute("UPDATE users SET org_id = ? WHERE id = ?", (org_id, user_id))
    conn.execute(
        "INSERT OR IGNORE INTO user_location_access (user_id, location_id, role) VALUES (?, ?, ?)",
        (user_id, location_id, role)
    )
    conn.commit()
    conn.close()


def get_user_role_in_org(user_id: int, org_id: int) -> Optional[str]:
    """Return the user's role in the org, or None."""
    conn = _get_conn()
    row = conn.execute("""
        SELECT ula.role FROM user_location_access ula
        JOIN locations l ON l.id = ula.location_id
        WHERE ula.user_id = ? AND l.org_id = ?
        LIMIT 1
    """, (user_id, org_id)).fetchone()
    conn.close()
    return row[0] if row else None


def get_org_members(org_id: int) -> List[dict]:
    """All members with their roles."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT u.id, u.name, u.email, ula.role
        FROM users u
        JOIN user_location_access ula ON ula.user_id = u.id
        JOIN locations l ON l.id = ula.location_id
        WHERE l.org_id = ?
        ORDER BY CASE ula.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, u.name
    """, (org_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_org_seat_usage(org_id: int) -> dict:
    """Return {used, limit, tier}."""
    conn = _get_conn()
    used = conn.execute("""
        SELECT COUNT(*) FROM user_location_access ula
        JOIN locations l ON l.id = ula.location_id
        WHERE l.org_id = ?
    """, (org_id,)).fetchone()[0]
    row = conn.execute("SELECT tier, seat_limit FROM orgs WHERE id = ?", (org_id,)).fetchone()
    conn.close()
    return {
        "used": used,
        "tier": row[0] if row else "starter",
        "limit": row[1] if row else 3,
    }


def get_invite_codes(org_id: int) -> List[dict]:
    """Active (unused, non-expired) invite codes."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT ic.code, ic.role, ic.expires_at, ic.created_at,
               u.name as created_by_name
        FROM invite_codes ic
        JOIN users u ON u.id = ic.created_by
        WHERE ic.org_id = ? AND ic.used_by IS NULL
          AND (ic.expires_at IS NULL OR ic.expires_at > datetime('now'))
        ORDER BY ic.created_at DESC
    """, (org_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_invite_code(code: str, org_id: int) -> bool:
    """Delete unused code. Returns True if deleted."""
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM invite_codes WHERE code = ? AND org_id = ? AND used_by IS NULL",
        (code, org_id)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def remove_org_member(user_id_to_remove: int, org_id: int, requesting_user_id: int) -> None:
    """Remove a member. Owner only. Cannot remove self."""
    if user_id_to_remove == requesting_user_id:
        raise ValueError("Cannot remove yourself")
    conn = _get_conn()
    loc_row = conn.execute("SELECT id FROM locations WHERE org_id = ? LIMIT 1", (org_id,)).fetchone()
    if not loc_row:
        conn.close()
        raise ValueError("Org not found")
    location_id = loc_row[0]
    conn.execute(
        "DELETE FROM user_location_access WHERE user_id = ? AND location_id = ?",
        (user_id_to_remove, location_id)
    )
    conn.commit()
    conn.close()
