"""
KPI storage module for maintenance analytics MVP.

This module handles persisting calculated KPI results to SQLite database,
managing daily, weekly, and monthly KPI tables with upsert functionality.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import pandas as pd


class KPIStorageError(Exception):
    """Custom exception for KPI storage errors."""
    pass


def get_database_path() -> Path:
    """
    Get the path to the SQLite database.
    
    Returns:
        Path object pointing to the database file
        
    Raises:
        KPIStorageError: If database file doesn't exist
    """
    # Assuming this script is in backend/, the database is in ../data/db/
    db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
    
    if not db_path.exists():
        raise KPIStorageError(f"Database file not found at {db_path}")
    
    return db_path


def create_kpi_tables(db_path: Optional[Path] = None) -> None:
    """
    Create KPI storage tables if they don't exist.
    
    Creates three tables: daily_kpis, weekly_kpis, monthly_kpis
    Each table stores KPI results with period tracking and metadata.
    
    Args:
        db_path: Optional path to database file. If None, uses default path.
        
    Raises:
        KPIStorageError: If table creation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Daily KPIs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_date DATE NOT NULL,
                kpi_name TEXT NOT NULL,
                raw_value REAL,
                truesignal_value REAL,
                distortion_flag BOOLEAN NOT NULL DEFAULT 0,
                explanation_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(period_date, kpi_name)
            )
        """)
        
        # Weekly KPIs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_week TEXT NOT NULL,
                kpi_name TEXT NOT NULL,
                raw_value REAL,
                truesignal_value REAL,
                distortion_flag BOOLEAN NOT NULL DEFAULT 0,
                explanation_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(period_week, kpi_name)
            )
        """)
        
        # Monthly KPIs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_month TEXT NOT NULL,
                kpi_name TEXT NOT NULL,
                raw_value REAL,
                truesignal_value REAL,
                distortion_flag BOOLEAN NOT NULL DEFAULT 0,
                explanation_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(period_month, kpi_name)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_kpis_period 
            ON daily_kpis(period_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_kpis_name 
            ON daily_kpis(kpi_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weekly_kpis_period 
            ON weekly_kpis(period_week)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weekly_kpis_name 
            ON weekly_kpis(kpi_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monthly_kpis_period 
            ON monthly_kpis(period_month)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monthly_kpis_name 
            ON monthly_kpis(kpi_name)
        """)
        
        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to create KPI tables: {str(e)}")


def _validate_kpi_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    """
    Validate that DataFrame has required columns for KPI storage.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Raises:
        KPIStorageError: If validation fails
    """
    if df.empty:
        raise KPIStorageError("Cannot store empty DataFrame")
    
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise KPIStorageError(
            f"DataFrame missing required columns: {missing_cols}"
        )


def _prepare_kpi_data(df: pd.DataFrame, period_col: str) -> pd.DataFrame:
    """
    Prepare KPI DataFrame for database insertion.
    
    Args:
        df: KPI DataFrame
        period_col: Name of the period column (period_date, period_week, period_month)
        
    Returns:
        Prepared DataFrame with proper data types
    """
    df_copy = df.copy()
    
    # Ensure distortion_flag is boolean/integer
    if 'distortion_flag' in df_copy.columns:
        df_copy['distortion_flag'] = df_copy['distortion_flag'].astype(int)
    
    # Ensure period column exists
    if period_col not in df_copy.columns:
        # If period column is missing, use current date/week/month
        current_date = datetime.now()
        if period_col == 'period_date':
            df_copy[period_col] = current_date.strftime('%Y-%m-%d')
        elif period_col == 'period_week':
            # Format: YYYY-WW
            df_copy[period_col] = current_date.strftime('%Y-%W')
        elif period_col == 'period_month':
            # Format: YYYY-MM
            df_copy[period_col] = current_date.strftime('%Y-%m')
    else:
        # Convert period column to string if it's a datetime
        if pd.api.types.is_datetime64_any_dtype(df_copy[period_col]):
            if period_col == 'period_date':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%m-%d')
            elif period_col == 'period_week':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%W')
            elif period_col == 'period_month':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%m')
    
    # Add created_at timestamp if not present, and convert to string
    if 'created_at' not in df_copy.columns:
        df_copy['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        # Convert created_at to string if it's a Timestamp
        if pd.api.types.is_datetime64_any_dtype(df_copy['created_at']):
            df_copy['created_at'] = df_copy['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return df_copy

def store_daily_kpis(df: pd.DataFrame, db_path: Optional[Path] = None) -> int:
    """
    Store daily KPI results to database.
    
    Upserts data - updates existing records or inserts new ones based on
    (period_date, kpi_name) uniqueness constraint.
    
    Args:
        df: DataFrame with columns: kpi_name, raw_value, truesignal_value,
            distortion_flag, explanation (and optionally period_date)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        Number of rows stored
        
    Raises:
        KPIStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate DataFrame
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 
                     'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    
    # Prepare data
    df_prepared = _prepare_kpi_data(df, 'period_date')
    
    # Rename explanation column if needed
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Use REPLACE to upsert (delete + insert)
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                REPLACE INTO daily_kpis 
                (period_date, kpi_name, raw_value, truesignal_value, 
                 distortion_flag, explanation_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['period_date'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                row['distortion_flag'],
                row.get('explanation_text', ''),
                row.get('created_at', datetime.now())
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to store daily KPIs: {str(e)}")


def store_weekly_kpis(df: pd.DataFrame, db_path: Optional[Path] = None) -> int:
    """
    Store weekly KPI results to database.
    
    Upserts data - updates existing records or inserts new ones based on
    (period_week, kpi_name) uniqueness constraint.
    
    Args:
        df: DataFrame with columns: kpi_name, raw_value, truesignal_value,
            distortion_flag, explanation (and optionally period_week)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        Number of rows stored
        
    Raises:
        KPIStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate DataFrame
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 
                     'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    
    # Prepare data
    df_prepared = _prepare_kpi_data(df, 'period_week')
    
    # Rename explanation column if needed
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Use REPLACE to upsert (delete + insert)
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                REPLACE INTO weekly_kpis 
                (period_week, kpi_name, raw_value, truesignal_value, 
                 distortion_flag, explanation_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['period_week'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                row['distortion_flag'],
                row.get('explanation_text', ''),
                row.get('created_at', datetime.now())
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to store weekly KPIs: {str(e)}")
def store_monthly_kpis(df: pd.DataFrame, db_path: Optional[Path] = None) -> int:
    """
    Store monthly KPI results to database.
    
    Upserts data - updates existing records or inserts new ones based on
    (period_month, kpi_name) uniqueness constraint.
    
    Args:
        df: DataFrame with columns: kpi_name, raw_value, truesignal_value,
            distortion_flag, explanation (and optionally period_month)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        Number of rows stored
        
    Raises:
        KPIStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate DataFrame
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 
                     'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    
    # Prepare data
    df_prepared = _prepare_kpi_data(df, 'period_month')
    
    # Rename explanation column if needed
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Use REPLACE to upsert (delete + insert)
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                REPLACE INTO monthly_kpis 
                (period_month, kpi_name, raw_value, truesignal_value, 
                 distortion_flag, explanation_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['period_month'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                row['distortion_flag'],
                row.get('explanation_text', ''),
                row.get('created_at', datetime.now())
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to store monthly KPIs: {str(e)}")


def retrieve_daily_kpis(
    period_date: Optional[str] = None,
    kpi_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Retrieve daily KPIs from database.
    
    Args:
        period_date: Optional filter by specific date (YYYY-MM-DD format)
        kpi_name: Optional filter by specific KPI name
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        DataFrame with daily KPI results
        
    Raises:
        KPIStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with optional filters
        query = "SELECT * FROM daily_kpis WHERE 1=1"
        params = []
        
        if period_date:
            query += " AND period_date = ?"
            params.append(period_date)
        
        if kpi_name:
            query += " AND kpi_name = ?"
            params.append(kpi_name)
        
        query += " ORDER BY period_date DESC, kpi_name"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to retrieve daily KPIs: {str(e)}")


def retrieve_weekly_kpis(
    period_week: Optional[str] = None,
    kpi_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Retrieve weekly KPIs from database.
    
    Args:
        period_week: Optional filter by specific week (YYYY-WW format)
        kpi_name: Optional filter by specific KPI name
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        DataFrame with weekly KPI results
        
    Raises:
        KPIStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with optional filters
        query = "SELECT * FROM weekly_kpis WHERE 1=1"
        params = []
        
        if period_week:
            query += " AND period_week = ?"
            params.append(period_week)
        
        if kpi_name:
            query += " AND kpi_name = ?"
            params.append(kpi_name)
        
        query += " ORDER BY period_week DESC, kpi_name"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to retrieve weekly KPIs: {str(e)}")


def retrieve_monthly_kpis(
    period_month: Optional[str] = None,
    kpi_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Retrieve monthly KPIs from database.
    
    Args:
        period_month: Optional filter by specific month (YYYY-MM format)
        kpi_name: Optional filter by specific KPI name
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        DataFrame with monthly KPI results
        
    Raises:
        KPIStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with optional filters
        query = "SELECT * FROM monthly_kpis WHERE 1=1"
        params = []
        
        if period_month:
            query += " AND period_month = ?"
            params.append(period_month)
        
        if kpi_name:
            query += " AND kpi_name = ?"
            params.append(kpi_name)
        
        query += " ORDER BY period_month DESC, kpi_name"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to retrieve monthly KPIs: {str(e)}")


def delete_kpis_by_period(
    table: str,
    period_value: str,
    db_path: Optional[Path] = None
) -> int:
    """
    Delete KPIs for a specific period from a table.
    
    Args:
        table: Table name ('daily_kpis', 'weekly_kpis', or 'monthly_kpis')
        period_value: Period value to delete (date, week, or month string)
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        Number of rows deleted
        
    Raises:
        KPIStorageError: If deletion fails or table name is invalid
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate table name
    valid_tables = {
        'daily_kpis': 'period_date',
        'weekly_kpis': 'period_week',
        'monthly_kpis': 'period_month'
    }
    
    if table not in valid_tables:
        raise KPIStorageError(
            f"Invalid table name: {table}. Must be one of {list(valid_tables.keys())}"
        )
    
    period_col = valid_tables[table]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            f"DELETE FROM {table} WHERE {period_col} = ?",
            (period_value,)
        )
        
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_deleted
        
    except sqlite3.Error as e:
        raise KPIStorageError(f"Failed to delete KPIs: {str(e)}")


if __name__ == "__main__":
    """
    Test KPI storage functionality.
    """
    try:
        print("Creating KPI tables...")
        create_kpi_tables()
        print("✓ Tables created successfully")
        
        # Test with sample data
        print("\nTesting with sample KPI data...")
        
        # Sample daily KPIs
        daily_data = pd.DataFrame([
            {
                'kpi_name': 'Reactive Work Ratio',
                'raw_value': 0.45,
                'truesignal_value': 0.38,
                'distortion_flag': True,
                'explanation': 'Test explanation for daily KPI'
            },
            {
                'kpi_name': 'PM Compliance (True)',
                'raw_value': 0.85,
                'truesignal_value': 0.72,
                'distortion_flag': True,
                'explanation': 'Test explanation for PM compliance'
            }
        ])
        
        rows = store_daily_kpis(daily_data)
        print(f"✓ Stored {rows} daily KPI records")
        
        # Sample weekly KPIs
        weekly_data = pd.DataFrame([
            {
                'kpi_name': 'PM Slippage Rate',
                'raw_value': 0.25,
                'truesignal_value': 0.18,
                'distortion_flag': True,
                'explanation': 'Test explanation for weekly KPI'
            }
        ])
        
        rows = store_weekly_kpis(weekly_data)
        print(f"✓ Stored {rows} weekly KPI records")
        
        # Sample monthly KPIs
        monthly_data = pd.DataFrame([
            {
                'kpi_name': 'PM Effectiveness Score',
                'raw_value': 0.90,
                'truesignal_value': 0.65,
                'distortion_flag': True,
                'explanation': 'Test explanation for monthly KPI'
            }
        ])
        
        rows = store_monthly_kpis(monthly_data)
        print(f"✓ Stored {rows} monthly KPI records")
        
        # Test retrieval
        print("\nRetrieving stored KPIs...")
        daily_kpis = retrieve_daily_kpis()
        print(f"✓ Retrieved {len(daily_kpis)} daily KPI records")
        
        weekly_kpis = retrieve_weekly_kpis()
        print(f"✓ Retrieved {len(weekly_kpis)} weekly KPI records")
        
        monthly_kpis = retrieve_monthly_kpis()
        print(f"✓ Retrieved {len(monthly_kpis)} monthly KPI records")
        
        print("\n" + "="*60)
        print("Sample Daily KPIs:")
        print("="*60)
        if not daily_kpis.empty:
            print(daily_kpis[['period_date', 'kpi_name', 'raw_value', 
                             'truesignal_value', 'distortion_flag']].to_string())
        
        print("\nKPI storage module is working correctly!")
        
    except KPIStorageError as e:
        print(f"ERROR: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        