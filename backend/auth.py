"""
Auth utilities -- password hashing, JWT, and multi-tenant user/org/location queries.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import sqlite3

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
    # Ensure columns exist for DBs that were created before multi-tenant
    for col, typedef in [("org_id", "INTEGER"), ("role", "TEXT DEFAULT 'member'")]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
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
            "INSERT INTO users (name, email, hashed_password, org_id, role) VALUES (?, ?, ?, ?, 'admin')",
            (name, email, hashed, org_id)
        )
        user_id = cur.lastrowid

        # Grant admin access to the location
        conn.execute(
            "INSERT INTO user_location_access (user_id, location_id, role) VALUES (?, ?, 'admin')",
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
