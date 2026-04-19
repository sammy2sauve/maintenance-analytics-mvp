"""
Database connection and query utilities for KPI API.

Uses Neon (PostgreSQL) via psycopg2. All SQLite references removed.
"""

from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

from .neon import get_conn


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Example:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM daily_kpis")
    """
    conn = None
    try:
        conn = get_conn()
        yield conn
    except psycopg2.Error as e:
        raise DatabaseError(f"Database connection error: {str(e)}")
    finally:
        if conn:
            conn.close()


def execute_query(
    query: str,
    params: Optional[tuple] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dicts.

    Parameters use %s placeholders (psycopg2 style).
    """
    if params is None:
        params = ()

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                # Convert distortion_flag int to bool if present
                if 'distortion_flag' in d and isinstance(d['distortion_flag'], int):
                    d['distortion_flag'] = bool(d['distortion_flag'])
                result.append(d)
            return result

    except psycopg2.Error as e:
        raise DatabaseError(f"Query execution failed: {str(e)}")


def get_daily_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
    days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM daily_kpis WHERE 1=1"
    params = []

    if kpi_name:
        query += " AND kpi_name = %s"
        params.append(kpi_name)

    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query += " AND period_date >= %s"
        params.append(cutoff)

    query += " ORDER BY period_date DESC, kpi_name LIMIT %s"
    params.append(limit)

    return execute_query(query, tuple(params))


def get_weekly_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM weekly_kpis WHERE 1=1"
    params = []

    if kpi_name:
        query += " AND kpi_name = %s"
        params.append(kpi_name)

    query += " ORDER BY period_week DESC, kpi_name LIMIT %s"
    params.append(limit)

    return execute_query(query, tuple(params))


def get_monthly_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM monthly_kpis WHERE 1=1"
    params = []

    if kpi_name:
        query += " AND kpi_name = %s"
        params.append(kpi_name)

    query += " ORDER BY period_month DESC, kpi_name LIMIT %s"
    params.append(limit)

    return execute_query(query, tuple(params))


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        results = execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
            (table_name,)
        )
        return len(results) > 0
    except DatabaseError:
        return False
