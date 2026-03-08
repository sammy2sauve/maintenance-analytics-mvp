"""
Auth utilities — password hashing and JWT creation/verification.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import sqlite3

import bcrypt
from jose import JWTError, jwt

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = "truesignal-dev-secret-change-in-prod"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

# ── DB setup ──────────────────────────────────────────────────────────────────

def init_users_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            email          TEXT UNIQUE NOT NULL,
            name           TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# ── JWT ───────────────────────────────────────────────────────────────────────

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

# ── User queries ──────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(name: str, email: str, password: str) -> dict:
    hashed = hash_password(password)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, hashed_password) VALUES (?, ?, ?)",
            (name, email, hashed)
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    return {"id": user_id, "name": name, "email": email}
