"""
Prediction storage module for maintenance analytics MVP.

This module handles persisting prediction results (asset failures, PM optimizations,
and insights) to SQLite database with retrieval functions.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd


class PredictionStorageError(Exception):
    """Custom exception for prediction storage errors."""
    pass


def get_database_path() -> Path:
    """
    Get the path to the SQLite database.
    
    Returns:
        Path object pointing to the database file
        
    Raises:
        PredictionStorageError: If database file doesn't exist
    """
    db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
    
    if not db_path.exists():
        raise PredictionStorageError(f"Database file not found at {db_path}")
    
    return db_path


def _prepare_prediction_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare prediction DataFrame for database insertion.
    
    Ensures all data types are compatible with SQLite.
    
    Args:
        df: Prediction DataFrame
        
    Returns:
        Prepared DataFrame with proper data types
    """
    df_copy = df.copy()
    
    # Convert any datetime columns to strings
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Ensure numeric columns are properly typed
    numeric_cols = ['failure_probability', 'confidence_score', 'mtbf_days', 
                    'estimated_cost_savings', 'estimated_risk_change', 'metric_value']
    
    for col in numeric_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    
    # Add created_at if not present
    if 'created_at' not in df_copy.columns:
        df_copy['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return df_copy


def store_failure_predictions(
    predictions_df: pd.DataFrame,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> int:
    """
    Store asset failure predictions to database.
    
    Uses REPLACE to upsert - updates existing predictions or inserts new ones
    based on (asset_id, prediction_date) uniqueness constraint.
    
    Args:
        predictions_df: DataFrame with failure predictions
        db_path: Optional path to database file
        
    Returns:
        Number of rows stored
        
    Raises:
        PredictionStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate required columns
    required_cols = [
        'asset_id', 'prediction_date', 'failure_probability', 
        'confidence_score', 'risk_level', 'recommendation'
    ]
    
    missing_cols = set(required_cols) - set(predictions_df.columns)
    if missing_cols:
        raise PredictionStorageError(
            f"Missing required columns: {missing_cols}"
        )
    
    if predictions_df.empty:
        return 0
    
    # Prepare data
    df_prepared = _prepare_prediction_data(predictions_df)
    
    try:
        conn = sqlite3.connect(db_path)
        rows_affected = 0
        
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                REPLACE INTO asset_failure_predictions (
                    asset_id, prediction_date, failure_probability,
                    confidence_score, days_to_predicted_failure, mtbf_days,
                    days_since_last_pm, reactive_work_count_90d, risk_level,
                    recommendation, created_at, location_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                row.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                location_id,
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to store failure predictions: {str(e)}")


def store_pm_optimization_suggestions(
    suggestions_df: pd.DataFrame,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> int:
    """
    Store PM optimization suggestions to database.
    
    Args:
        suggestions_df: DataFrame with PM optimization suggestions
        db_path: Optional path to database file
        
    Returns:
        Number of rows stored
        
    Raises:
        PredictionStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate required columns
    required_cols = [
        'asset_id', 'current_pm_frequency_days', 
        'suggested_pm_frequency_days', 'reason', 'suggestion_date'
    ]
    
    missing_cols = set(required_cols) - set(suggestions_df.columns)
    if missing_cols:
        raise PredictionStorageError(
            f"Missing required columns: {missing_cols}"
        )
    
    if suggestions_df.empty:
        return 0
    
    # Prepare data
    df_prepared = _prepare_prediction_data(suggestions_df)
    
    try:
        conn = sqlite3.connect(db_path)
        rows_affected = 0
        
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            # Preserve existing accepted/implemented status — don't overwrite with 'pending'
            existing = cursor.execute(
                "SELECT status FROM pm_optimization_suggestions WHERE asset_id=? AND location_id=?",
                (row['asset_id'], location_id)
            ).fetchone()
            status = existing[0] if existing and existing[0] != 'pending' else row.get('status', 'pending')
            cursor.execute("""
                REPLACE INTO pm_optimization_suggestions (
                    asset_id, current_pm_frequency_days,
                    suggested_pm_frequency_days, reason,
                    estimated_cost_savings, estimated_risk_change,
                    confidence_score, reactive_work_after_pm_count,
                    suggestion_date, status, created_at, location_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                row.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                location_id,
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to store PM suggestions: {str(e)}")


def store_maintenance_insights(
    insights_df: pd.DataFrame,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> int:
    """
    Store maintenance insights to database.
    
    Args:
        insights_df: DataFrame with maintenance insights
        db_path: Optional path to database file
        
    Returns:
        Number of rows stored
        
    Raises:
        PredictionStorageError: If storage operation fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    # Validate required columns
    required_cols = [
        'insight_type', 'title', 'description', 'insight_date'
    ]
    
    missing_cols = set(required_cols) - set(insights_df.columns)
    if missing_cols:
        raise PredictionStorageError(
            f"Missing required columns: {missing_cols}"
        )
    
    if insights_df.empty:
        return 0
    
    # Prepare data
    df_prepared = _prepare_prediction_data(insights_df)
    
    try:
        conn = sqlite3.connect(db_path)
        rows_affected = 0
        
        for _, row in df_prepared.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                REPLACE INTO maintenance_insights (
                    insight_type, title, description,
                    confidence_score, impact_level, affected_assets,
                    metric_value, insight_date, created_at, location_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['insight_type'],
                row['title'],
                row['description'],
                row.get('confidence_score'),
                row.get('impact_level'),
                row.get('affected_assets'),
                row.get('metric_value'),
                row['insight_date'],
                row.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                location_id,
            ))
            rows_affected += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected
        
    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to store insights: {str(e)}")
    # ============================================================================
# RETRIEVAL FUNCTIONS
# ============================================================================

def retrieve_failure_predictions(
    asset_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_probability: Optional[float] = None,
    limit: int = 100,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Retrieve asset failure predictions from database.
    
    Args:
        asset_id: Optional filter by specific asset
        risk_level: Optional filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)
        min_probability: Optional minimum failure probability threshold
        limit: Maximum number of records to return
        db_path: Optional path to database file
        
    Returns:
        DataFrame with failure predictions
        
    Raises:
        PredictionStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with filters
        query = "SELECT * FROM asset_failure_predictions WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = ?"
            params.append(location_id)

        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)

        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level.upper())

        if min_probability is not None:
            query += " AND failure_probability >= ?"
            params.append(min_probability)

        query += " ORDER BY failure_probability DESC, prediction_date DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Convert numeric columns to object dtype so NaN can become None
        # (pandas keeps NaN in float64 columns even after .where(notna(), None))
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)

        return df

    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to retrieve failure predictions: {str(e)}")


def retrieve_pm_optimization_suggestions(
    asset_id: Optional[str] = None,
    status: str = 'pending',
    min_savings: Optional[float] = None,
    limit: int = 100,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Retrieve PM optimization suggestions from database.
    
    Args:
        asset_id: Optional filter by specific asset
        status: Filter by status (pending, accepted, rejected)
        min_savings: Optional minimum cost savings threshold
        limit: Maximum number of records to return
        db_path: Optional path to database file
        
    Returns:
        DataFrame with PM optimization suggestions
        
    Raises:
        PredictionStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with filters
        query = "SELECT * FROM pm_optimization_suggestions WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = ?"
            params.append(location_id)

        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        if min_savings is not None:
            query += " AND estimated_cost_savings >= ?"
            params.append(min_savings)

        query += " ORDER BY estimated_cost_savings DESC, suggestion_date DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Convert numeric columns to object dtype so NaN can become None
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)

        return df

    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to retrieve PM suggestions: {str(e)}")


def retrieve_maintenance_insights(
    insight_type: Optional[str] = None,
    impact_level: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Retrieve maintenance insights from database.
    
    Args:
        insight_type: Optional filter by insight type
        impact_level: Optional filter by impact level (LOW, MEDIUM, HIGH)
        limit: Maximum number of records to return
        db_path: Optional path to database file
        
    Returns:
        DataFrame with maintenance insights
        
    Raises:
        PredictionStorageError: If retrieval fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Build query with filters
        query = "SELECT * FROM maintenance_insights WHERE 1=1"
        params = []

        if location_id is not None:
            query += " AND location_id = ?"
            params.append(location_id)

        if insight_type:
            query += " AND insight_type = ?"
            params.append(insight_type)

        if impact_level:
            query += " AND impact_level = ?"
            params.append(impact_level.upper())

        query += " ORDER BY insight_date DESC, confidence_score DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Convert numeric columns to object dtype so NaN can become None
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(object)
        df = df.where(df.notna(), None)

        return df

    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to retrieve insights: {str(e)}")


def get_high_risk_assets(
    min_probability: float = 0.5,
    limit: int = 50,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Get assets with high failure risk.

    Convenience function for retrieving critical and high-risk assets.
    """
    return retrieve_failure_predictions(
        min_probability=min_probability,
        limit=limit,
        db_path=db_path,
        location_id=location_id,
    )


def get_cost_saving_opportunities(
    min_savings: float = 100.0,
    limit: int = 50,
    db_path: Optional[Path] = None,
    location_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Get PM optimization suggestions with significant cost savings.

    Convenience function for retrieving top cost-saving opportunities.
    """
    return retrieve_pm_optimization_suggestions(
        status='pending',
        min_savings=min_savings,
        limit=limit,
        db_path=db_path,
        location_id=location_id,
    )


def update_suggestion_status(
    suggestion_id: int,
    new_status: str,
    db_path: Optional[Path] = None
) -> bool:
    """
    Update the status of a PM optimization suggestion.
    
    Useful for tracking which suggestions have been implemented.
    
    Args:
        suggestion_id: ID of the suggestion to update
        new_status: New status (pending, accepted, rejected, implemented)
        db_path: Optional path to database file
        
    Returns:
        True if update successful
        
    Raises:
        PredictionStorageError: If update fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    valid_statuses = ['pending', 'accepted', 'rejected', 'implemented']
    if new_status not in valid_statuses:
        raise PredictionStorageError(
            f"Invalid status: {new_status}. Must be one of {valid_statuses}"
        )
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pm_optimization_suggestions
            SET status = ?
            WHERE id = ?
        """, (new_status, suggestion_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
        
    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to update suggestion status: {str(e)}")


def delete_old_predictions(
    days_to_keep: int = 90,
    db_path: Optional[Path] = None
) -> Dict[str, int]:
    """
    Delete old prediction data to keep database clean.
    
    Args:
        days_to_keep: Number of days of predictions to keep (default 90)
        db_path: Optional path to database file
        
    Returns:
        Dictionary with count of deleted records per table
        
    Raises:
        PredictionStorageError: If deletion fails
    """
    if db_path is None:
        db_path = get_database_path()
    
    cutoff_date = (datetime.now() - pd.Timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        deleted_counts = {}
        
        # Delete old predictions
        cursor.execute("""
            DELETE FROM asset_failure_predictions
            WHERE prediction_date < ?
        """, (cutoff_date,))
        deleted_counts['predictions'] = cursor.rowcount
        
        # Delete old suggestions
        cursor.execute("""
            DELETE FROM pm_optimization_suggestions
            WHERE suggestion_date < ?
        """, (cutoff_date,))
        deleted_counts['suggestions'] = cursor.rowcount
        
        # Delete old insights
        cursor.execute("""
            DELETE FROM maintenance_insights
            WHERE insight_date < ?
        """, (cutoff_date,))
        deleted_counts['insights'] = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_counts
        
    except sqlite3.Error as e:
        raise PredictionStorageError(f"Failed to delete old predictions: {str(e)}")


if __name__ == "__main__":
    """
    Test prediction storage functions.
    """
    try:
        from load_and_map_data import load_and_prepare_data
        from predictive_analytics import (
            predict_asset_failures,
            optimize_pm_schedules,
            generate_maintenance_insights
        )
        
        print("="*70)
        print("TESTING PREDICTION STORAGE")
        print("="*70)
        
        # Load data and generate predictions
        print("\n1. Loading data and generating predictions...")
        df = load_and_prepare_data()
        
        predictions = predict_asset_failures(df)
        print(f"✓ Generated {len(predictions)} failure predictions")
        
        suggestions = optimize_pm_schedules(df)
        print(f"✓ Generated {len(suggestions)} PM suggestions")
        
        insights = generate_maintenance_insights(df)
        print(f"✓ Generated {len(insights)} insights")
        
        # Store predictions
        print("\n2. Storing predictions to database...")
        
        pred_rows = store_failure_predictions(predictions)
        print(f"✓ Stored {pred_rows} failure predictions")
        
        sugg_rows = store_pm_optimization_suggestions(suggestions)
        print(f"✓ Stored {sugg_rows} PM suggestions")
        
        insight_rows = store_maintenance_insights(insights)
        print(f"✓ Stored {insight_rows} insights")
        
        # Retrieve predictions
        print("\n3. Testing retrieval functions...")
        
        high_risk = get_high_risk_assets(min_probability=0.5)
        print(f"✓ Retrieved {len(high_risk)} high-risk assets")
        
        if not high_risk.empty:
            print(f"\n   Top risk asset: {high_risk.iloc[0]['asset_id']}")
            print(f"   Probability: {high_risk.iloc[0]['failure_probability']:.2%}")
            print(f"   Risk Level: {high_risk.iloc[0]['risk_level']}")
        
        savings = get_cost_saving_opportunities(min_savings=50)
        print(f"\n✓ Retrieved {len(savings)} cost-saving opportunities")
        
        if not savings.empty:
            total_savings = savings['estimated_cost_savings'].sum()
            print(f"   Total potential savings: ${total_savings:.2f}")
        
        all_insights = retrieve_maintenance_insights()
        print(f"\n✓ Retrieved {len(all_insights)} insights")
        
        if not all_insights.empty:
            print(f"\n   Latest insight: {all_insights.iloc[0]['title']}")
        
        print("\n" + "="*70)
        print("✅ ALL STORAGE TESTS PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        