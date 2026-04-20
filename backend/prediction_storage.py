"""
Prediction storage module — persists prediction results to Neon (PostgreSQL).
"""

import psycopg2
import psycopg2.extras
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

from .neon import get_conn


class PredictionStorageError(Exception):
    pass


def _prepare_prediction_data(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    numeric_cols = ['failure_probability', 'confidence_score', 'mtbf_days',
                    'estimated_cost_savings', 'estimated_risk_change', 'metric_value']
    for col in numeric_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    if 'created_at' not in df_copy.columns:
        df_copy['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return df_copy


def store_failure_predictions(
    predictions_df: pd.DataFrame,
    location_id: Optional[int] = None,
) -> int:
    required_cols = ['asset_id', 'prediction_date', 'failure_probability',
                     'confidence_score', 'risk_level', 'recommendation']
    missing_cols = set(required_cols) - set(predictions_df.columns)
    if missing_cols:
        raise PredictionStorageError(f"Missing required columns: {missing_cols}")
    if predictions_df.empty:
        return 0

    df_prepared = _prepare_prediction_data(predictions_df)

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cur.execute("""
                INSERT INTO asset_failure_predictions (
                    asset_id, prediction_date, failure_probability,
                    confidence_score, days_to_predicted_failure, mtbf_days,
                    days_since_last_pm, reactive_work_count_90d, risk_level,
                    recommendation, location_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_id, prediction_date, location_id) DO UPDATE SET
                    failure_probability       = EXCLUDED.failure_probability,
                    confidence_score          = EXCLUDED.confidence_score,
                    days_to_predicted_failure = EXCLUDED.days_to_predicted_failure,
                    mtbf_days                 = EXCLUDED.mtbf_days,
                    days_since_last_pm        = EXCLUDED.days_since_last_pm,
                    reactive_work_count_90d   = EXCLUDED.reactive_work_count_90d,
                    risk_level                = EXCLUDED.risk_level,
                    recommendation            = EXCLUDED.recommendation
            """, (
                row['asset_id'],
                row['prediction_date'],
                row['failure_probability'],
                row['confidence_score'],
                row.get('days_to_predicted_failure'),
                row.get('mtbf_days'),
                row.get('days_since_last_pm'),
                row.get('reactive_work_count_90d'),
                row['risk_level'],
                row['recommendation'],
                location_id,
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to store failure predictions: {str(e)}")


def store_pm_optimization_suggestions(
    suggestions_df: pd.DataFrame,
    location_id: Optional[int] = None,
) -> int:
    required_cols = ['asset_id', 'current_pm_frequency_days',
                     'suggested_pm_frequency_days', 'reason', 'suggestion_date']
    missing_cols = set(required_cols) - set(suggestions_df.columns)
    if missing_cols:
        raise PredictionStorageError(f"Missing required columns: {missing_cols}")
    if suggestions_df.empty:
        return 0

    df_prepared = _prepare_prediction_data(suggestions_df)

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            # Preserve non-pending status (accepted/implemented) — don't overwrite
            cur.execute(
                "SELECT status FROM pm_optimization_suggestions WHERE asset_id=%s AND location_id=%s",
                (row['asset_id'], location_id)
            )
            existing = cur.fetchone()
            status = (existing['status']
                      if existing and existing['status'] != 'pending'
                      else row.get('status', 'pending'))

            cur.execute("""
                INSERT INTO pm_optimization_suggestions (
                    asset_id, current_pm_frequency_days,
                    suggested_pm_frequency_days, reason,
                    estimated_cost_savings, estimated_risk_change,
                    confidence_score, reactive_work_after_pm_count,
                    suggestion_date, status, location_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_id, location_id) DO UPDATE SET
                    current_pm_frequency_days   = EXCLUDED.current_pm_frequency_days,
                    suggested_pm_frequency_days = EXCLUDED.suggested_pm_frequency_days,
                    reason                      = EXCLUDED.reason,
                    estimated_cost_savings      = EXCLUDED.estimated_cost_savings,
                    estimated_risk_change       = EXCLUDED.estimated_risk_change,
                    confidence_score            = EXCLUDED.confidence_score,
                    reactive_work_after_pm_count = EXCLUDED.reactive_work_after_pm_count,
                    suggestion_date             = EXCLUDED.suggestion_date,
                    status                      = EXCLUDED.status
            """, (
                row['asset_id'],
                row['current_pm_frequency_days'],
                row['suggested_pm_frequency_days'],
                row['reason'],
                row.get('estimated_cost_savings'),
                row.get('estimated_risk_change'),
                row.get('confidence_score'),
                row.get('reactive_work_after_pm_count'),
                row['suggestion_date'],
                status,
                location_id,
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to store PM suggestions: {str(e)}")


def store_maintenance_insights(
    insights_df: pd.DataFrame,
    location_id: Optional[int] = None,
) -> int:
    required_cols = ['insight_type', 'title', 'description', 'insight_date']
    missing_cols = set(required_cols) - set(insights_df.columns)
    if missing_cols:
        raise PredictionStorageError(f"Missing required columns: {missing_cols}")
    if insights_df.empty:
        return 0

    df_prepared = _prepare_prediction_data(insights_df)

    try:
        conn = get_conn()
        cur = conn.cursor()
        rows_affected = 0
        for _, row in df_prepared.iterrows():
            cur.execute("""
                INSERT INTO maintenance_insights (
                    insight_type, title, description,
                    confidence_score, impact_level, affected_assets,
                    metric_value, insight_date, location_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (insight_type, title, location_id) DO UPDATE SET
                    description      = EXCLUDED.description,
                    confidence_score = EXCLUDED.confidence_score,
                    impact_level     = EXCLUDED.impact_level,
                    affected_assets  = EXCLUDED.affected_assets,
                    metric_value     = EXCLUDED.metric_value,
                    insight_date     = EXCLUDED.insight_date
            """, (
                row['insight_type'],
                row['title'],
                row['description'],
                row.get('confidence_score'),
                row.get('impact_level'),
                row.get('affected_assets'),
                row.get('metric_value'),
                row['insight_date'],
                location_id,
            ))
            rows_affected += cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to store insights: {str(e)}")


def retrieve_failure_predictions(
    asset_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_probability: Optional[float] = None,
    limit: int = 100,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        query = "SELECT * FROM asset_failure_predictions WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = %s"
            params.append(location_id)
        if asset_id:
            query += " AND asset_id = %s"
            params.append(asset_id)
        if risk_level:
            query += " AND risk_level = %s"
            params.append(risk_level.upper())
        if min_probability is not None:
            query += " AND failure_probability >= %s"
            params.append(min_probability)

        query += " ORDER BY failure_probability DESC, prediction_date DESC LIMIT %s"
        params.append(limit)

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)
        return df

    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to retrieve failure predictions: {str(e)}")


def retrieve_pm_optimization_suggestions(
    asset_id: Optional[str] = None,
    status: str = 'pending',
    min_savings: Optional[float] = None,
    limit: int = 100,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        query = "SELECT * FROM pm_optimization_suggestions WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = %s"
            params.append(location_id)
        if asset_id:
            query += " AND asset_id = %s"
            params.append(asset_id)
        if status:
            query += " AND status = %s"
            params.append(status)
        if min_savings is not None:
            query += " AND estimated_cost_savings >= %s"
            params.append(min_savings)

        query += " ORDER BY estimated_cost_savings DESC, suggestion_date DESC LIMIT %s"
        params.append(limit)

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)
        return df

    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to retrieve PM suggestions: {str(e)}")


def retrieve_maintenance_insights(
    insight_type: Optional[str] = None,
    impact_level: Optional[str] = None,
    limit: int = 100,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    try:
        conn = get_conn()
        query = "SELECT * FROM maintenance_insights WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = %s"
            params.append(location_id)
        if insight_type:
            query += " AND insight_type = %s"
            params.append(insight_type)
        if impact_level:
            query += " AND impact_level = %s"
            params.append(impact_level.upper())

        query += " ORDER BY insight_date DESC, confidence_score DESC LIMIT %s"
        params.append(limit)

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)
        return df

    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to retrieve insights: {str(e)}")


def get_high_risk_assets(
    min_probability: float = 0.5,
    limit: int = 50,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    return retrieve_failure_predictions(
        min_probability=min_probability,
        limit=limit,
        location_id=location_id,
    )


def get_cost_saving_opportunities(
    min_savings: float = 100.0,
    limit: int = 50,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    return retrieve_pm_optimization_suggestions(
        status='pending',
        min_savings=min_savings,
        limit=limit,
        location_id=location_id,
    )


def update_suggestion_status(suggestion_id: int, new_status: str) -> bool:
    valid_statuses = ['pending', 'accepted', 'rejected', 'implemented']
    if new_status not in valid_statuses:
        raise PredictionStorageError(f"Invalid status: {new_status}")

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE pm_optimization_suggestions SET status = %s WHERE id = %s",
            (new_status, suggestion_id)
        )
        rows_affected = cur.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to update suggestion status: {str(e)}")


def delete_old_predictions(days_to_keep: int = 90) -> Dict[str, int]:
    cutoff_date = (datetime.now() - pd.Timedelta(days=days_to_keep)).strftime('%Y-%m-%d')

    try:
        conn = get_conn()
        cur = conn.cursor()
        deleted_counts = {}

        cur.execute("DELETE FROM asset_failure_predictions WHERE prediction_date < %s", (cutoff_date,))
        deleted_counts['predictions'] = cur.rowcount

        cur.execute("DELETE FROM pm_optimization_suggestions WHERE suggestion_date < %s", (cutoff_date,))
        deleted_counts['suggestions'] = cur.rowcount

        cur.execute("DELETE FROM maintenance_insights WHERE insight_date < %s", (cutoff_date,))
        deleted_counts['insights'] = cur.rowcount

        conn.commit()
        conn.close()
        return deleted_counts
    except psycopg2.Error as e:
        raise PredictionStorageError(f"Failed to delete old predictions: {str(e)}")
