"""
Auth utilities -- password hashing, JWT, and multi-tenant user/org/location queries.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import secrets

import bcrypt
import psycopg2
from jose import JWTError, jwt

from .encryption import encrypt, decrypt
from .neon import get_conn

# -- Config -------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "truesignal-dev-secret-change-in-prod")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7


# -- DB setup -----------------------------------------------------------------

def _get_conn():
    return get_conn()


def init_users_table():
    """Ensure all multi-tenant tables exist in Neon (idempotent)."""
    from .create_schema_neon import create_schema
    create_schema()


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
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_locations(user_id: int) -> List[dict]:
    """Return all locations the user has access to."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.org_id, l.name,
               (l.mx_api_key_enc IS NOT NULL) as has_api_key,
               ula.role as access_role,
               o.plan,
               o.trial_ends_at,
               o.extra_seats,
               o.seat_limit
        FROM locations l
        JOIN user_location_access ula ON ula.location_id = l.id
        JOIN orgs o ON o.id = l.org_id
        WHERE ula.user_id = %s
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    result = []
    from datetime import timezone
    now = __import__('datetime').datetime.now(timezone.utc)
    for r in rows:
        d = dict(r)
        trial_ends = d.get('trial_ends_at')
        if trial_ends and hasattr(trial_ends, 'tzinfo') and trial_ends.tzinfo is None:
            trial_ends = trial_ends.replace(tzinfo=timezone.utc)
        trial_days_left = max(0, (trial_ends - now).days) if trial_ends else 0
        d['trial_days_left'] = trial_days_left
        d['trial_ends_at'] = trial_ends.isoformat() if trial_ends else None
        result.append(d)
    return result


# -- API key storage (on location, not user) ----------------------------------

def save_location_api_key(location_id: int, plaintext_key: str) -> None:
    """Encrypt and store the location's MaintainX API key."""
    enc, salt, nonce = encrypt(plaintext_key)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE locations SET mx_api_key_enc=%s, mx_api_key_salt=%s, mx_api_key_nonce=%s WHERE id=%s",
        (enc, salt, nonce, location_id)
    )
    conn.commit()
    conn.close()


def get_location_api_key(location_id: int) -> Optional[str]:
    """Decrypt and return the API key for a location. Server-side only."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT mx_api_key_enc, mx_api_key_salt, mx_api_key_nonce FROM locations WHERE id=%s",
        (location_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row or row['mx_api_key_enc'] is None:
        return None
    return decrypt(row['mx_api_key_enc'], row['mx_api_key_salt'], row['mx_api_key_nonce'])


def location_has_api_key(location_id: int) -> bool:
    """Check if a location has a stored API key. Safe for frontend."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT mx_api_key_enc FROM locations WHERE id=%s", (location_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row['mx_api_key_enc'] is not None)


def delete_location_api_key(location_id: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE locations SET mx_api_key_enc=NULL, mx_api_key_salt=NULL, mx_api_key_nonce=NULL WHERE id=%s",
        (location_id,)
    )
    conn.commit()
    conn.close()


def user_can_access_location(user_id: int, location_id: int) -> bool:
    """Check if user has access to a given location."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM user_location_access WHERE user_id=%s AND location_id=%s",
        (user_id, location_id)
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


# -- Backward-compat wrappers -------------------------------------------------

def has_api_key(user_id: int) -> bool:
    """Check if user's first location has an API key."""
    locs = get_user_locations(user_id)
    if not locs:
        return False
    return bool(locs[0]["has_api_key"])


def save_user_api_key(user_id: int, plaintext_key: str) -> None:
    locs = get_user_locations(user_id)
    if not locs:
        return
    save_location_api_key(locs[0]["id"], plaintext_key)


def get_user_api_key(user_id: int) -> Optional[str]:
    locs = get_user_locations(user_id)
    if not locs:
        return None
    return get_location_api_key(locs[0]["id"])


def delete_user_api_key(user_id: int) -> None:
    locs = get_user_locations(user_id)
    if not locs:
        return
    delete_location_api_key(locs[0]["id"])


# -- User creation (multi-tenant) ---------------------------------------------

def create_user(name: str, email: str, password: str, org_name: str = None) -> dict:
    """
    Create a new user with org + location in one transaction.
    Returns a verification_token that should be emailed to the user.
    """
    hashed = hash_password(password)
    if not org_name:
        org_name = f"{name}'s Organization"
    verification_token = secrets.token_urlsafe(32)

    conn = _get_conn()
    cur = conn.cursor()
    try:
        # Create org — 30-day trial starts on signup
        cur.execute("""
            INSERT INTO orgs (name, plan, trial_ends_at)
            VALUES (%s, 'trial', NOW() + INTERVAL '30 days')
            RETURNING id
        """, (org_name,))
        org_id = cur.fetchone()['id']

        # Create default location
        cur.execute(
            "INSERT INTO locations (org_id, name) VALUES (%s, %s) RETURNING id",
            (org_id, "Default Location")
        )
        location_id = cur.fetchone()['id']

        # Create user
        cur.execute(
            """INSERT INTO users (name, email, hashed_password, org_id, role, email_verification_token)
               VALUES (%s, %s, %s, %s, 'owner', %s) RETURNING id""",
            (name, email, hashed, org_id, verification_token)
        )
        user_id = cur.fetchone()['id']

        # Grant owner access to the location
        cur.execute(
            "INSERT INTO user_location_access (user_id, location_id, role) VALUES (%s, %s, 'owner')",
            (user_id, location_id)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "org_id": org_id,
        "location_id": location_id,
        "verification_token": verification_token,
    }


# -- Invite codes & team management ------------------------------------------

def create_user_shell(name: str, email: str, password: str) -> dict:
    """Create a bare user row with no org/location (invited user path)."""
    hashed = hash_password(password)
    verification_token = secrets.token_urlsafe(32)
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO users (name, email, hashed_password, role, email_verification_token)
               VALUES (%s, %s, %s, 'member', %s) RETURNING id""",
            (name, email, hashed, verification_token)
        )
        user_id = cur.fetchone()['id']
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"id": user_id, "name": name, "email": email, "verification_token": verification_token}


def create_invite_code(org_id: int, location_id: int, created_by: int,
                       role: str = 'viewer', expires_days: int = 7) -> str:
    """Generate an invite code after checking seat limit."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT seat_limit FROM orgs WHERE id = %s", (org_id,))
        row = cur.fetchone()
        seat_limit = row['seat_limit'] if row and row['seat_limit'] is not None else None
        if seat_limit is not None:
            cur.execute("""
                SELECT COUNT(*) FROM user_location_access ula
                JOIN locations l ON l.id = ula.location_id
                WHERE l.org_id = %s
            """, (org_id,))
            used = cur.fetchone()['count']
            cur.execute("""
                SELECT COUNT(*) FROM invite_codes
                WHERE org_id = %s AND used_by IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
            """, (org_id,))
            pending = cur.fetchone()['count']
            if used + pending >= seat_limit:
                raise ValueError(f"Seat limit of {seat_limit} reached")

        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
        code = secrets.token_urlsafe(24)
        cur.execute(
            "INSERT INTO invite_codes (code, org_id, location_id, role, created_by, expires_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (code, org_id, location_id, role, created_by, expires_at)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return code


def validate_invite_code(code: str) -> Optional[dict]:
    """Return invite details or None if invalid/used/expired."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT ic.id, ic.code, ic.org_id, ic.location_id, ic.role, ic.used_by, ic.expires_at,
               o.name as org_name, o.tier, o.seat_limit
        FROM invite_codes ic
        JOIN orgs o ON o.id = ic.org_id
        WHERE ic.code = %s
          AND ic.used_by IS NULL
          AND (ic.expires_at IS NULL OR ic.expires_at > NOW())
    """, (code,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def accept_invite_code(code: str, user_id: int) -> None:
    """Mark code used, set user org_id, insert location access."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT org_id, location_id, role FROM invite_codes WHERE code = %s AND used_by IS NULL",
            (code,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Invite code not found or already used")
        org_id, location_id, role = row['org_id'], row['location_id'], row['role']
        cur.execute("UPDATE invite_codes SET used_by = %s WHERE code = %s", (user_id, code))
        cur.execute("UPDATE users SET org_id = %s WHERE id = %s", (org_id, user_id))
        cur.execute(
            "INSERT INTO user_location_access (user_id, location_id, role) VALUES (%s, %s, %s) ON CONFLICT (user_id, location_id) DO NOTHING",
            (user_id, location_id, role)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_password_reset_token(email: str) -> Optional[str]:
    """
    Generate a 1-hour password reset token for the given email.
    Returns the token string, or None if the email doesn't exist.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    cur.execute(
        "UPDATE users SET password_reset_token = %s, password_reset_expires_at = %s WHERE id = %s",
        (token, expires, row["id"]),
    )
    conn.commit()
    conn.close()
    return token


def reset_password_with_token(token: str, new_password: str) -> Optional[dict]:
    """
    Validate a password reset token and set a new password.
    Returns the user dict on success, None if the token is invalid/expired.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, password_reset_expires_at FROM users WHERE password_reset_token = %s",
        (token,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    expires = row["password_reset_expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        conn.close()
        return None  # expired
    new_hash = hash_password(new_password)
    cur.execute(
        "UPDATE users SET hashed_password = %s, password_reset_token = NULL, password_reset_expires_at = NULL WHERE id = %s",
        (new_hash, row["id"]),
    )
    conn.commit()
    conn.close()
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def verify_email_token(token: str) -> Optional[dict]:
    """
    Look up user by verification token, mark as verified, clear the token.
    Returns the user dict on success, None if token is invalid.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email FROM users WHERE email_verification_token = %s",
        (token,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    user = dict(row)
    cur.execute(
        "UPDATE users SET email_verified = TRUE, email_verification_token = NULL WHERE id = %s",
        (user['id'],)
    )
    conn.commit()
    conn.close()
    return user


def get_user_role_in_org(user_id: int, org_id: int) -> Optional[str]:
    """Return the user's role in the org, or None."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT ula.role FROM user_location_access ula
        JOIN locations l ON l.id = ula.location_id
        WHERE ula.user_id = %s AND l.org_id = %s
        LIMIT 1
    """, (user_id, org_id))
    row = cur.fetchone()
    conn.close()
    return row['role'] if row else None


def get_org_members(org_id: int) -> List[dict]:
    """All members with their roles."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.name, u.email, ula.role
        FROM users u
        JOIN user_location_access ula ON ula.user_id = u.id
        JOIN locations l ON l.id = ula.location_id
        WHERE l.org_id = %s
        ORDER BY CASE ula.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, u.name
    """, (org_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_org_seat_usage(org_id: int) -> dict:
    """Return {used, limit, tier}."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM user_location_access ula
        JOIN locations l ON l.id = ula.location_id
        WHERE l.org_id = %s
    """, (org_id,))
    used = cur.fetchone()['count']
    cur.execute("SELECT tier, seat_limit FROM orgs WHERE id = %s", (org_id,))
    row = cur.fetchone()
    conn.close()
    return {
        "used": used,
        "tier": row['tier'] if row else "starter",
        "limit": row['seat_limit'] if row else 3,
    }


def get_invite_codes(org_id: int) -> List[dict]:
    """Active (unused, non-expired) invite codes."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT ic.code, ic.role, ic.expires_at, ic.created_at,
               u.name as created_by_name
        FROM invite_codes ic
        JOIN users u ON u.id = ic.created_by
        WHERE ic.org_id = %s AND ic.used_by IS NULL
          AND (ic.expires_at IS NULL OR ic.expires_at > NOW())
        ORDER BY ic.created_at DESC
    """, (org_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_invite_code(code: str, org_id: int) -> bool:
    """Delete unused code. Returns True if deleted."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM invite_codes WHERE code = %s AND org_id = %s AND used_by IS NULL",
        (code, org_id)
    )
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def remove_org_member(user_id_to_remove: int, org_id: int, requesting_user_id: int) -> None:
    """Remove a member. Owner only. Cannot remove self."""
    if user_id_to_remove == requesting_user_id:
        raise ValueError("Cannot remove yourself")
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM locations WHERE org_id = %s LIMIT 1", (org_id,))
    loc_row = cur.fetchone()
    if not loc_row:
        conn.close()
        raise ValueError("Org not found")
    location_id = loc_row['id']
    cur.execute(
        "DELETE FROM user_location_access WHERE user_id = %s AND location_id = %s",
        (user_id_to_remove, location_id)
    )
    conn.commit()
    conn.close()
