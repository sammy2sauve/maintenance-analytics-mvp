"""
Central Neon/PostgreSQL connection for TrueSignal.

All backend modules import get_conn() or get_db() from here.
DATABASE_URL is loaded from .env (or the real environment in production).
"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Add it to .env")


def get_conn():
    """Open a new psycopg2 connection with RealDictCursor (rows behave like dicts)."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def get_db():
    """
    Context manager: commits on clean exit, rolls back on exception.

    Usage:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
    """
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
