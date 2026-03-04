"""
Database connection and query utilities for KPI API.

This module provides safe SQLite database access with connection management
and result formatting for the FastAPI service.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime, timedelta


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


def get_database_path() -> Path:
    """
    Get the path to the SQLite database.
    
    Returns:
        Path object pointing to the database file
        
    Raises:
        DatabaseError: If database file doesn't exist
    """
    # Assuming this script is in backend/, the database is in ../data/db/
    db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
    
    if not db_path.exists():
        raise DatabaseError(f"Database file not found at {db_path}")
    
    return db_path


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """
    Context manager for database connections.
    
    Ensures connections are properly closed even if errors occur.
    
    Args:
        db_path: Optional path to database file. If None, uses default path.
        
    Yields:
        SQLite connection object
        
    Raises:
        DatabaseError: If connection fails
        
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_kpis")
    """
    if db_path is None:
        db_path = get_database_path()
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Database connection error: {str(e)}")
    finally:
        if conn:
            conn.close()


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """
    Convert SQLite row to dictionary with type conversions.
    
    Args:
        cursor: SQLite cursor object
        row: Row tuple from query result
        
    Returns:
        Dictionary with column names as keys
    """
    fields = [column[0] for column in cursor.description]
    result = {}
    
    for key, value in zip(fields, row):
        # Convert integer flags to boolean
        if key == 'distortion_flag' and isinstance(value, int):
            result[key] = bool(value)
        else:
            result[key] = value
    
    return result

def execute_query(
    query: str,
    params: Optional[tuple] = None,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries.
    
    Args:
        query: SQL SELECT query string
        params: Optional tuple of query parameters
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        List of dictionaries, one per row
        
    Raises:
        DatabaseError: If query execution fails
        
    Example:
        results = execute_query(
            "SELECT * FROM daily_kpis WHERE kpi_name = ?",
            ("Reactive Work Ratio",)
        )
    """
    if params is None:
        params = ()
    
    try:
        with get_db_connection(db_path) as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
            
    except sqlite3.Error as e:
        raise DatabaseError(f"Query execution failed: {str(e)}")


def get_daily_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
    days: Optional[int] = None,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve daily KPIs from database.

    Args:
        kpi_name: Optional filter by specific KPI name
        limit: Maximum number of records to return (default 100)
        days: Optional number of days to look back (e.g. 7, 30, 90)
        db_path: Optional path to database file. If None, uses default path.

    Returns:
        List of daily KPI records as dictionaries

    Raises:
        DatabaseError: If query fails
    """
    query = "SELECT * FROM daily_kpis WHERE 1=1"
    params = []

    if kpi_name:
        query += " AND kpi_name = ?"
        params.append(kpi_name)

    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query += " AND period_date >= ?"
        params.append(cutoff)

    query += " ORDER BY period_date DESC, kpi_name LIMIT ?"
    params.append(limit)

    return execute_query(query, tuple(params), db_path)


def get_weekly_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve weekly KPIs from database.
    
    Args:
        kpi_name: Optional filter by specific KPI name
        limit: Maximum number of records to return (default 100)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        List of weekly KPI records as dictionaries
        
    Raises:
        DatabaseError: If query fails
    """
    query = "SELECT * FROM weekly_kpis WHERE 1=1"
    params = []
    
    if kpi_name:
        query += " AND kpi_name = ?"
        params.append(kpi_name)
    
    query += " ORDER BY period_week DESC, kpi_name LIMIT ?"
    params.append(limit)
    
    return execute_query(query, tuple(params), db_path)


def get_monthly_kpis(
    kpi_name: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve monthly KPIs from database.
    
    Args:
        kpi_name: Optional filter by specific KPI name
        limit: Maximum number of records to return (default 100)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        List of monthly KPI records as dictionaries
        
    Raises:
        DatabaseError: If query fails
    """
    query = "SELECT * FROM monthly_kpis WHERE 1=1"
    params = []
    
    if kpi_name:
        query += " AND kpi_name = ?"
        params.append(kpi_name)
    
    query += " ORDER BY period_month DESC, kpi_name LIMIT ?"
    params.append(limit)
    
    return execute_query(query, tuple(params), db_path)


def table_exists(table_name: str, db_path: Optional[Path] = None) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table to check
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        True if table exists, False otherwise
    """
    try:
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        results = execute_query(query, (table_name,), db_path)
        return len(results) > 0
    except DatabaseError:
        return False


if __name__ == "__main__":
    """
    Test database connection and queries.
    """
    try:
        print("Testing database connection...")
        
        # Test connection
        with get_db_connection() as conn:
            print("✓ Database connection successful")
        
        # Check if tables exist
        tables = ['daily_kpis', 'weekly_kpis', 'monthly_kpis']
        for table in tables:
            exists = table_exists(table)
            status = "✓" if exists else "✗"
            print(f"{status} Table '{table}' exists: {exists}")
        
        # Test queries
        print("\nTesting queries...")
        
        daily = get_daily_kpis(limit=5)
        print(f"✓ Retrieved {len(daily)} daily KPI records")
        
        weekly = get_weekly_kpis(limit=5)
        print(f"✓ Retrieved {len(weekly)} weekly KPI records")
        
        monthly = get_monthly_kpis(limit=5)
        print(f"✓ Retrieved {len(monthly)} monthly KPI records")
        
        if daily:
            print("\nSample daily KPI record:")
            print(daily[0])
        
        print("\nDatabase module is working correctly!")
        
    except DatabaseError as e:
        print(f"ERROR: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")