"""
KPI storage module — persists calculated KPI results to Neon (PostgreSQL).
"""

import psycopg2
from typing import Optional, List
from datetime import datetime
import pandas as pd

from .neon import get_conn


class KPIStorageError(Exception):
    pass


def create_kpi_tables() -> None:
    """Create KPI tables in Neon if they don't exist (idempotent)."""
    from .create_schema_neon import create_schema
    create_schema()


def _validate_kpi_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    if df.empty:
        raise KPIStorageError("Cannot store empty DataFrame")
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise KPIStorageError(f"DataFrame missing required columns: {missing_cols}")


def _prepare_kpi_data(df: pd.DataFrame, period_col: str) -> pd.DataFrame:
    df_copy = df.copy()

    if 'distortion_flag' in df_copy.columns:
        df_copy['distortion_flag'] = df_copy['distortion_flag'].astype(bool)

    if period_col not in df_copy.columns:
        current_date = datetime.now()
        if period_col == 'period_date':
            df_copy[period_col] = current_date.strftime('%Y-%m-%d')
        elif period_col == 'period_week':
            df_copy[period_col] = current_date.strftime('%Y-%W')
        elif period_col == 'period_month':
            df_copy[period_col] = current_date.strftime('%Y-%m')
    else:
        if pd.api.types.is_datetime64_any_dtype(df_copy[period_col]):
            if period_col == 'period_date':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%m-%d')
            elif period_col == 'period_week':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%W')
            elif period_col == 'period_month':
                df_copy[period_col] = df_copy[period_col].dt.strftime('%Y-%m')

    return df_copy


def store_daily_kpis(df: pd.DataFrame) -> int:
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    df_prepared = _prepare_kpi_data(df, 'period_date')
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cur.execute("""
                INSERT INTO daily_kpis
                    (period_date, kpi_name, raw_value, truesignal_value, distortion_flag, explanation_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (period_date, kpi_name) DO UPDATE SET
                    raw_value        = EXCLUDED.raw_value,
                    truesignal_value = EXCLUDED.truesignal_value,
                    distortion_flag  = EXCLUDED.distortion_flag,
                    explanation_text = EXCLUDED.explanation_text
            """, (
                row['period_date'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                bool(row['distortion_flag']),
                row.get('explanation_text', ''),
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to store daily KPIs: {str(e)}")


def store_weekly_kpis(df: pd.DataFrame) -> int:
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    df_prepared = _prepare_kpi_data(df, 'period_week')
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cur.execute("""
                INSERT INTO weekly_kpis
                    (period_week, kpi_name, raw_value, truesignal_value, distortion_flag, explanation_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (period_week, kpi_name) DO UPDATE SET
                    raw_value        = EXCLUDED.raw_value,
                    truesignal_value = EXCLUDED.truesignal_value,
                    distortion_flag  = EXCLUDED.distortion_flag,
                    explanation_text = EXCLUDED.explanation_text
            """, (
                row['period_week'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                bool(row['distortion_flag']),
                row.get('explanation_text', ''),
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to store weekly KPIs: {str(e)}")


def store_monthly_kpis(df: pd.DataFrame) -> int:
    required_cols = ['kpi_name', 'raw_value', 'truesignal_value', 'distortion_flag', 'explanation']
    _validate_kpi_dataframe(df, required_cols)
    df_prepared = _prepare_kpi_data(df, 'period_month')
    if 'explanation' in df_prepared.columns and 'explanation_text' not in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'explanation': 'explanation_text'})

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cur.execute("""
                INSERT INTO monthly_kpis
                    (period_month, kpi_name, raw_value, truesignal_value, distortion_flag, explanation_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (period_month, kpi_name) DO UPDATE SET
                    raw_value        = EXCLUDED.raw_value,
                    truesignal_value = EXCLUDED.truesignal_value,
                    distortion_flag  = EXCLUDED.distortion_flag,
                    explanation_text = EXCLUDED.explanation_text
            """, (
                row['period_month'],
                row['kpi_name'],
                row['raw_value'],
                row['truesignal_value'],
                bool(row['distortion_flag']),
                row.get('explanation_text', ''),
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to store monthly KPIs: {str(e)}")


def retrieve_daily_kpis(
    period_date: Optional[str] = None,
    kpi_name: Optional[str] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor()
        query = "SELECT * FROM daily_kpis WHERE 1=1"
        params = []
        if period_date:
            query += " AND period_date = %s"
            params.append(period_date)
        if kpi_name:
            query += " AND kpi_name = %s"
            params.append(kpi_name)
        query += " ORDER BY period_date DESC, kpi_name"
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to retrieve daily KPIs: {str(e)}")


def retrieve_weekly_kpis(
    period_week: Optional[str] = None,
    kpi_name: Optional[str] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor()
        query = "SELECT * FROM weekly_kpis WHERE 1=1"
        params = []
        if period_week:
            query += " AND period_week = %s"
            params.append(period_week)
        if kpi_name:
            query += " AND kpi_name = %s"
            params.append(kpi_name)
        query += " ORDER BY period_week DESC, kpi_name"
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to retrieve weekly KPIs: {str(e)}")


def retrieve_monthly_kpis(
    period_month: Optional[str] = None,
    kpi_name: Optional[str] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor()
        query = "SELECT * FROM monthly_kpis WHERE 1=1"
        params = []
        if period_month:
            query += " AND period_month = %s"
            params.append(period_month)
        if kpi_name:
            query += " AND kpi_name = %s"
            params.append(kpi_name)
        query += " ORDER BY period_month DESC, kpi_name"
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to retrieve monthly KPIs: {str(e)}")


def delete_kpis_by_period(table: str, period_value: str) -> int:
    valid_tables = {
        'daily_kpis': 'period_date',
        'weekly_kpis': 'period_week',
        'monthly_kpis': 'period_month'
    }
    if table not in valid_tables:
        raise KPIStorageError(f"Invalid table name: {table}")
    period_col = valid_tables[table]
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table} WHERE {period_col} = %s", (period_value,))
        rows_deleted = cur.rowcount
        conn.commit()
        conn.close()
        return rows_deleted
    except psycopg2.Error as e:
        raise KPIStorageError(f"Failed to delete KPIs: {str(e)}")
