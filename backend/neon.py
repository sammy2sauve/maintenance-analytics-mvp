"""
Central Neon/PostgreSQL connection for TrueSignal.

All backend modules import get_conn() or get_db() from here.
DATABASE_URL is loaded from .env (or the real environment in production).

Uses a ThreadedConnectionPool so connections are reused across requests
instead of opening a new TCP+TLS handshake on every API call.
"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Add it to .env")

_pool = psycopg2.pool.ThreadedConnectionPool(
    2, 10,  # min 2, max 10 connections
    DATABASE_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
)


class _PooledConnection:
    """Wraps a psycopg2 connection so conn.close() returns it to the pool."""
    def __init__(self, conn):
        self._conn = conn

    def close(self):
        try:
            if not self._conn.closed:
                self._conn.rollback()  # clean state before returning
        except Exception:
            pass
        _pool.putconn(self._conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _get_live_conn():
    """Get a connection from the pool, replacing it if Neon has closed it."""
    conn = _pool.getconn()
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        # Stale connection — discard and open a fresh one
        try:
            _pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return conn


def get_conn():
    """Get a pooled connection. Call conn.close() to return it to the pool."""
    return _PooledConnection(_get_live_conn())


@contextmanager
def get_db():
    """
    Context manager: commits on clean exit, rolls back on exception,
    always returns connection to pool.

    Usage:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
    """
    conn = _get_live_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.rollback()  # ensure clean state
        except Exception:
            pass
        _pool.putconn(conn)
