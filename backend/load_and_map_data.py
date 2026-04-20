"""
Data ingestion and mapping module — loads work orders from Neon (PostgreSQL).
"""

import psycopg2
from typing import Optional
import pandas as pd
import numpy as np

from .neon import get_conn


class DataLoadError(Exception):
    pass


def load_work_orders_from_db() -> pd.DataFrame:
    """
    Load work_orders table from Neon PostgreSQL.

    Returns:
        DataFrame containing raw work orders data

    Raises:
        DataLoadError: If connection fails or table is empty
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Check table exists
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'work_orders'
        """)
        if not cur.fetchone():
            conn.close()
            raise DataLoadError("work_orders table not found in database. Run create_schema_neon first.")

        cur.execute("SELECT * FROM work_orders")
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        df = pd.DataFrame(rows, columns=cols)

        if df.empty:
            raise DataLoadError("work_orders table is empty. Sync CMMS data first.")

        return df

    except psycopg2.Error as e:
        raise DataLoadError(f"Database connection error: {str(e)}")


COLUMN_MAPPING = {
    'work_order_id':          'work_order_id',
    'asset_id':               'asset_id',
    'site':                   'site',
    'type':                   'type',
    'status':                 'status',
    'technician':             'technician',
    'creation_date':          'creation_date',
    'scheduled_start':        'scheduled_start',
    'start_date':             'start_date',
    'completion_date':        'completion_date',
    'labor_hours_scheduled':  'labor_hours_scheduled',
    'labor_hours_actual':     'labor_hours_actual',
    'downtime_hours':         'downtime_hours',
    'reactive_followup':      'reactive_followup',
    'priority':               'priority',
    'due_date':               'due_date',
}


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to internal schema. Already aligned for this project."""
    df_mapped = df.rename(columns=COLUMN_MAPPING)
    return df_mapped


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize work order data for KPI calculations."""
    df_clean = df.copy()

    # Date columns
    date_cols = ['creation_date', 'scheduled_start', 'start_date',
                 'completion_date', 'due_date']
    for col in date_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

    # Numeric columns
    numeric_cols = ['labor_hours_scheduled', 'labor_hours_actual', 'downtime_hours']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Standardize status and type strings
    if 'status' in df_clean.columns:
        df_clean['status'] = df_clean['status'].str.strip().str.title()
    if 'type' in df_clean.columns:
        df_clean['type'] = df_clean['type'].str.strip().str.title()
    if 'priority' in df_clean.columns:
        df_clean['priority'] = df_clean['priority'].str.strip().str.title()

    # Boolean-ish reactive_followup
    if 'reactive_followup' in df_clean.columns:
        df_clean['reactive_followup'] = df_clean['reactive_followup'].fillna(0).astype(int)

    return df_clean


def load_and_prepare_data() -> pd.DataFrame:
    """
    Full pipeline: load from DB, map columns, clean.

    Returns:
        Clean DataFrame ready for KPI calculation

    Raises:
        DataLoadError: If loading or cleaning fails
    """
    try:
        raw_df = load_work_orders_from_db()
        mapped_df = map_columns(raw_df)
        clean_df = clean_data(mapped_df)

        if clean_df.empty:
            raise DataLoadError("No data after cleaning")

        return clean_df

    except DataLoadError:
        raise
    except Exception as e:
        raise DataLoadError(f"Failed to load and prepare data: {str(e)}")
