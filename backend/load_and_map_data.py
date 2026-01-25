"""
Data ingestion and mapping module for maintenance analytics MVP.

This module handles loading work order data from SQLite database,
mapping columns to expected KPI schema, and cleaning data for analysis.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np


class DataLoadError(Exception):
    """Custom exception for data loading errors."""
    pass


def get_database_path() -> Path:
    """
    Get the path to the SQLite database.
    
    Returns:
        Path object pointing to the database file
        
    Raises:
        DataLoadError: If database file doesn't exist
    """
    # Assuming this script is in backend/, the database is in ../data/db/
    db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
    
    if not db_path.exists():
        raise DataLoadError(f"Database file not found at {db_path}")
    
    return db_path


def load_work_orders_from_db(db_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load work orders table from SQLite database.
    
    Args:
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        DataFrame containing raw work orders data
        
    Raises:
        DataLoadError: If database connection fails, table doesn't exist, or data is empty
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Check if work_orders table exists
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='work_orders'"
        )
        if not cursor.fetchone():
            raise DataLoadError("Table 'work_orders' not found in database")
        
        # Load the table
        df = pd.read_sql_query("SELECT * FROM work_orders", conn)
        conn.close()
        
        if df.empty:
            raise DataLoadError("Work orders table is empty")
        
        return df
        
    except sqlite3.Error as e:
        raise DataLoadError(f"Database error: {str(e)}")
    except Exception as e:
        raise DataLoadError(f"Error loading data: {str(e)}")


def map_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map database column names to expected KPI schema.
    
    Handles common variations in column naming conventions.
    
    Args:
        df: Raw DataFrame from database
        
    Returns:
        DataFrame with standardized column names
    """
    # Define mapping rules for common variations
    column_mapping = {
        # Date columns
        'created_date': 'creation_date',
        'created_at': 'creation_date',
        'schedule_start': 'scheduled_start',
        'scheduled_date': 'scheduled_start',
        'actual_start': 'start_date',
        'started_date': 'start_date',
        'completed_date': 'completion_date',
        'completed_at': 'completion_date',
        'finish_date': 'completion_date',
        'due': 'due_date',
        
        # Labor hours
        'scheduled_hours': 'labor_hours_scheduled',
        'planned_hours': 'labor_hours_scheduled',
        'actual_hours': 'labor_hours_actual',
        'hours_worked': 'labor_hours_actual',
        
        # Other fields
        'work_order_type': 'type',
        'wo_type': 'type',
        'order_type': 'type',
        'work_type': 'type',
        'followup': 'reactive_followup',
        'is_followup': 'reactive_followup',
    }
    
    # Create case-insensitive mapping
    df_columns_lower = {col.lower(): col for col in df.columns}
    
    # Apply mapping
    rename_dict = {}
    for old_name, new_name in column_mapping.items():
        if old_name.lower() in df_columns_lower:
            actual_col = df_columns_lower[old_name.lower()]
            rename_dict[actual_col] = new_name
    
    df = df.rename(columns=rename_dict)
    
    return df


def create_priority_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create priority column based on work order type.
    
    Maps: emergency -> emergency, pm/reactive -> normal
    
    Args:
        df: DataFrame with 'type' column
        
    Returns:
        DataFrame with added 'priority' column
    """
    if 'type' not in df.columns:
        # If no type column, default to normal priority
        df['priority'] = 'normal'
        return df
    
    # Convert type to lowercase for consistent mapping
    type_lower = df['type'].astype(str).str.lower().str.strip()
    
    # Map types to priorities
    priority_map = {
        'emergency': 'emergency',
        'urgent': 'emergency',
        'critical': 'emergency',
        'pm': 'normal',
        'preventive': 'normal',
        'preventative': 'normal',
        'reactive': 'normal',
        'corrective': 'normal',
        'breakdown': 'normal',
    }
    
    df['priority'] = type_lower.map(priority_map).fillna('normal')
    
    return df


def fill_missing_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing date columns with reasonable defaults.
    
    - If start_date is missing, use scheduled_start
    - If due_date is missing, use scheduled_start or creation_date + 7 days
    
    Args:
        df: DataFrame with date columns
        
    Returns:
        DataFrame with filled date columns
    """
    # Convert date columns to datetime
    date_columns = ['creation_date', 'scheduled_start', 'start_date', 
                    'completion_date', 'due_date']
    
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Fill start_date with scheduled_start if missing
    if 'start_date' in df.columns and 'scheduled_start' in df.columns:
        df['start_date'] = df['start_date'].fillna(df['scheduled_start'])
    elif 'start_date' not in df.columns and 'scheduled_start' in df.columns:
        df['start_date'] = df['scheduled_start']
    
    # Fill due_date if missing
    if 'due_date' not in df.columns or df['due_date'].isna().all():
        if 'scheduled_start' in df.columns:
            df['due_date'] = df['scheduled_start']
        elif 'creation_date' in df.columns:
            df['due_date'] = df['creation_date'] + pd.Timedelta(days=7)
    else:
        # Fill remaining NaN values in due_date
        if 'scheduled_start' in df.columns:
            df['due_date'] = df['due_date'].fillna(df['scheduled_start'])
        elif 'creation_date' in df.columns:
            df['due_date'] = df['due_date'].fillna(
                df['creation_date'] + pd.Timedelta(days=7)
            )
    
    return df


def validate_and_clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean the mapped data.
    
    - Ensure numeric columns are properly typed
    - Remove invalid records if necessary
    - Add any missing expected columns with defaults
    
    Args:
        df: Mapped DataFrame
        
    Returns:
        Cleaned and validated DataFrame
    """
    # Ensure numeric columns are numeric
    numeric_columns = ['labor_hours_scheduled', 'labor_hours_actual', 'downtime_hours']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Ensure boolean column for reactive_followup
    if 'reactive_followup' in df.columns:
        df['reactive_followup'] = df['reactive_followup'].astype(str).str.lower()
        df['reactive_followup'] = df['reactive_followup'].isin(['true', '1', 'yes', 't'])
    else:
        df['reactive_followup'] = False
    
    # Add missing expected columns with defaults
    expected_columns = {
        'labor_hours_scheduled': 0.0,
        'labor_hours_actual': 0.0,
        'downtime_hours': 0.0,
        'reactive_followup': False,
    }
    
    for col, default_value in expected_columns.items():
        if col not in df.columns:
            df[col] = default_value
    
    return df


def load_and_prepare_data(db_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Main function to load, map, and clean work orders data.
    
    This is the primary entry point for data ingestion. It orchestrates
    all the data loading, mapping, and cleaning steps.
    
    Args:
        db_path: Optional path to database file. If None, uses default path.
        
    Returns:
        Cleaned DataFrame ready for KPI calculations
        
    Raises:
        DataLoadError: If any step in the data loading process fails
        
    Example:
        >>> df = load_and_prepare_data()
        >>> print(df.columns)
        >>> # Use df for KPI calculations
    """
    # Load raw data
    df = load_work_orders_from_db(db_path)
    
    # Map column names
    df = map_column_names(df)
    
    # Create priority column
    df = create_priority_column(df)
    
    # Fill missing dates
    df = fill_missing_dates(df)
    
    # Validate and clean
    df = validate_and_clean_data(df)
    
    return df


if __name__ == "__main__":
    """
    Test the data loading and mapping functionality.
    """
    try:
        df = load_and_prepare_data()
        print("Data loaded successfully!")
        print(f"\nShape: {df.shape}")
        print(f"\nColumns: {df.columns.tolist()}")
        print(f"\nFirst few rows:\n{df.head()}")
        print(f"\nData types:\n{df.dtypes}")
        print(f"\nMissing values:\n{df.isna().sum()}")
        
    except DataLoadError as e:
        print(f"Error loading data: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")