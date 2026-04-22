"""
Prediction API endpoints for maintenance analytics MVP.

This module provides REST API endpoints for accessing failure predictions,
PM optimization suggestions, and maintenance insights.

These endpoints can be integrated into the main API or run standalone.
"""

import math
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Import prediction utilities
try:
    from prediction_storage import (
        retrieve_failure_predictions,
        retrieve_pm_optimization_suggestions,
        retrieve_maintenance_insights,
        get_high_risk_assets,
        get_cost_saving_opportunities,
        update_suggestion_status,
        PredictionStorageError
    )
except ImportError:
    from backend.prediction_storage import (
        retrieve_failure_predictions,
        retrieve_pm_optimization_suggestions,
        retrieve_maintenance_insights,
        get_high_risk_assets,
        get_cost_saving_opportunities,
        update_suggestion_status,
        PredictionStorageError
    )


def _clean_records(records: list) -> list:
    """Replace NaN/inf float values with None so Pydantic can serialize them."""
    cleaned = []
    for row in records:
        cleaned.append({
            k: (None if isinstance(v, float) and not math.isfinite(v) else v)
            for k, v in row.items()
        })
    return cleaned


# Create API router
router = APIRouter(prefix="/predictions", tags=["Predictions"])


# ============================================================================
# PYDANTIC MODELS FOR API RESPONSES
# ============================================================================

class FailurePrediction(BaseModel):
    """Model for asset failure prediction."""
    id: Optional[int] = None
    asset_id: str
    prediction_date: Union[str, date, datetime]
    failure_probability: float = Field(..., ge=0, le=1)
    confidence_score: float = Field(..., ge=0, le=1)
    days_to_predicted_failure: Optional[int] = None
    mtbf_days: Optional[float] = None
    days_since_last_pm: Optional[int] = None
    reactive_work_count_90d: Optional[int] = None
    risk_level: str
    recommendation: str
    created_at: Optional[Union[str, date, datetime]] = None


class PMOptimizationSuggestion(BaseModel):
    """Model for PM schedule optimization suggestion."""
    id: Optional[int] = None
    asset_id: str
    current_pm_frequency_days: int
    suggested_pm_frequency_days: int
    reason: str
    estimated_cost_savings: Optional[float] = None
    estimated_risk_change: Optional[float] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    reactive_work_after_pm_count: Optional[int] = None
    suggestion_date: Union[str, date, datetime]
    status: str = "pending"
    created_at: Optional[Union[str, date, datetime]] = None


class MaintenanceInsight(BaseModel):
    """Model for maintenance insight."""
    id: Optional[int] = None
    insight_type: str
    title: str
    description: str
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    impact_level: Optional[str] = None
    affected_assets: Optional[str] = None
    metric_value: Optional[float] = None
    insight_date: Union[str, date, datetime]
    created_at: Optional[Union[str, date, datetime]] = None


class SuggestionStatusUpdate(BaseModel):
    """Model for updating suggestion status."""
    status: str = Field(..., pattern="^(pending|accepted|rejected|implemented)$")


class PredictionSummary(BaseModel):
    """Model for prediction summary statistics."""
    total_assets_monitored: int
    high_risk_assets: int
    critical_risk_assets: int
    total_cost_savings_potential: float
    pending_suggestions: int
    latest_insights: int


# ============================================================================
# FAILURE PREDICTION ENDPOINTS
# ============================================================================

@router.get(
    "/failures",
    response_model=List[FailurePrediction],
    summary="Get asset failure predictions",
    description="Retrieve failure predictions with optional filtering by asset, risk level, or probability"
)
async def get_failure_predictions(
    asset_id: Optional[str] = Query(
        None,
        description="Filter by specific asset ID"
    ),
    risk_level: Optional[str] = Query(
        None,
        pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$",
        description="Filter by risk level"
    ),
    min_probability: Optional[float] = Query(
        None,
        ge=0,
        le=1,
        description="Minimum failure probability threshold"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of predictions to return"
    ),
    days: Optional[int] = Query(
        None,
        ge=1,
        description="Only return predictions from the last N days"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Retrieve asset failure predictions.

    Returns predictions sorted by failure probability (highest risk first).
    """
    try:
        from .neon import get_conn as _get_conn
        conn = _get_conn()
        cur = conn.cursor()

        filters, params = ["1=1"], []
        if location_id  is not None: filters.append("location_id = %s");          params.append(location_id)
        if asset_id:                 filters.append("asset_id = %s");             params.append(asset_id)
        if risk_level:               filters.append("risk_level = %s");           params.append(risk_level.upper())
        if min_probability is not None: filters.append("failure_probability >= %s"); params.append(min_probability)
        if days:                     filters.append("prediction_date >= %s");     params.append((datetime.now() - timedelta(days=days)).date())

        where = " AND ".join(filters)
        # DISTINCT ON deduplicates to latest prediction per asset in SQL
        cur.execute(f"""
            SELECT DISTINCT ON (asset_id)
                asset_id, prediction_date, failure_probability, confidence_score,
                days_to_predicted_failure, mtbf_days, days_since_last_pm,
                reactive_work_count_90d, risk_level, recommendation, location_id
            FROM asset_failure_predictions
            WHERE {where}
            ORDER BY asset_id, prediction_date DESC, failure_probability DESC
        """, params)
        rows = cur.fetchall()
        conn.close()

        # Sort by failure_probability DESC then apply limit
        rows.sort(key=lambda r: r['failure_probability'] or 0, reverse=True)
        return [dict(r) for r in rows[:limit]]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/failures/high-risk",
    response_model=List[FailurePrediction],
    summary="Get high-risk assets",
    description="Retrieve assets with high or critical failure risk (probability >= 50%)"
)
async def get_high_risk_assets_endpoint(
    min_probability: float = Query(
        0.5,
        ge=0,
        le=1,
        description="Minimum failure probability (default 0.5)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of assets to return"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Get assets with high failure risk.

    Convenience endpoint for monitoring critical assets.
    """
    try:
        df = get_high_risk_assets(
            min_probability=min_probability,
            limit=limit,
            location_id=location_id,
        )
        
        if df.empty:
            return []
        
        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve high-risk assets: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/failures/{asset_id}",
    response_model=FailurePrediction,
    summary="Get failure prediction for specific asset",
    description="Retrieve the latest failure prediction for a single asset"
)
async def get_asset_failure_prediction(
    asset_id: str
) -> Dict[str, Any]:
    """
    Get failure prediction for a specific asset.
    """
    try:
        df = retrieve_failure_predictions(
            asset_id=asset_id,
            limit=1
        )
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction found for asset {asset_id}"
            )
        
        return df.iloc[0].to_dict()
        
    except HTTPException:
        raise
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve prediction: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# PM OPTIMIZATION ENDPOINTS
# ============================================================================

@router.get(
    "/pm-optimization",
    response_model=List[PMOptimizationSuggestion],
    summary="Get PM optimization suggestions",
    description="Retrieve PM schedule optimization suggestions with optional filtering"
)
async def get_pm_optimization_suggestions_endpoint(
    asset_id: Optional[str] = Query(
        None,
        description="Filter by specific asset ID"
    ),
    status: str = Query(
        "pending",
        pattern="^(pending|accepted|rejected|implemented)$",
        description="Filter by suggestion status"
    ),
    min_savings: Optional[float] = Query(
        None,
        ge=0,
        description="Minimum cost savings threshold"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of suggestions to return"
    ),
    days: Optional[int] = Query(
        None,
        ge=1,
        description="Only return suggestions from the last N days"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Retrieve PM optimization suggestions.

    Returns suggestions sorted by cost savings (highest first).
    """
    try:
        from .neon import get_conn as _get_conn
        conn = _get_conn()
        cur = conn.cursor()

        filters, params = ["1=1"], []
        if location_id  is not None: filters.append("location_id = %s");             params.append(location_id)
        if asset_id:                 filters.append("asset_id = %s");                params.append(asset_id)
        if status:                   filters.append("status = %s");                  params.append(status)
        if min_savings is not None:  filters.append("estimated_cost_savings >= %s"); params.append(min_savings)
        if days:                     filters.append("suggestion_date >= %s");        params.append((datetime.now() - timedelta(days=days)).date())

        where = " AND ".join(filters)
        params.append(limit)
        cur.execute(f"""
            SELECT * FROM pm_optimization_suggestions
            WHERE {where}
            ORDER BY estimated_cost_savings DESC, suggestion_date DESC
            LIMIT %s
        """, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/pm-optimization/cost-savings",
    response_model=List[PMOptimizationSuggestion],
    summary="Get cost-saving opportunities",
    description="Retrieve PM suggestions with significant cost savings potential"
)
async def get_cost_savings_endpoint(
    min_savings: float = Query(
        100.0,
        ge=0,
        description="Minimum cost savings threshold (default $100)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of suggestions to return"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Get cost-saving opportunities.

    Convenience endpoint for identifying top savings opportunities.
    """
    try:
        df = get_cost_saving_opportunities(
            min_savings=min_savings,
            limit=limit,
            location_id=location_id,
        )
        
        if df.empty:
            return []
        
        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cost savings: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
@router.patch(
    "/pm-optimization/{suggestion_id}/status",
    summary="Update suggestion status",
    description="Update the status of a PM optimization suggestion (pending, accepted, rejected, implemented)"
)
async def update_pm_suggestion_status(
    suggestion_id: int,
    status_update: SuggestionStatusUpdate
) -> Dict[str, Any]:
    """
    Update the status of a PM optimization suggestion.
    
    Useful for tracking which suggestions have been reviewed or implemented.
    """
    try:
        success = update_suggestion_status(
            suggestion_id=suggestion_id,
            new_status=status_update.status
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Suggestion {suggestion_id} not found"
            )
        
        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "new_status": status_update.status,
            "message": f"Status updated to {status_update.status}"
        }
        
    except HTTPException:
        raise
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update suggestion status: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# MAINTENANCE INSIGHTS ENDPOINTS
# ============================================================================

@router.get(
    "/insights",
    response_model=List[MaintenanceInsight],
    summary="Get maintenance insights",
    description="Retrieve maintenance insights with optional filtering by type or impact level"
)
async def get_maintenance_insights_endpoint(
    insight_type: Optional[str] = Query(
        None,
        description="Filter by insight type (day_of_week_pattern, technician_performance, asset_reliability)"
    ),
    impact_level: Optional[str] = Query(
        None,
        pattern="^(LOW|MEDIUM|HIGH)$",
        description="Filter by impact level"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of insights to return"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Retrieve maintenance insights.

    Returns insights sorted by date and confidence score.
    """
    try:
        from .neon import get_conn as _get_conn
        conn = _get_conn()
        cur = conn.cursor()

        filters, params = ["1=1"], []
        if location_id  is not None: filters.append("location_id = %s");   params.append(location_id)
        if insight_type:             filters.append("insight_type = %s");  params.append(insight_type)
        if impact_level:             filters.append("impact_level = %s");  params.append(impact_level.upper())

        where = " AND ".join(filters)
        params.append(limit)
        cur.execute(f"""
            SELECT * FROM maintenance_insights
            WHERE {where}
            ORDER BY insight_date DESC, confidence_score DESC
            LIMIT %s
        """, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/insights/high-impact",
    response_model=List[MaintenanceInsight],
    summary="Get high-impact insights",
    description="Retrieve insights with high impact level"
)
async def get_high_impact_insights(
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of insights to return"
    ),
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> List[Dict[str, Any]]:
    """
    Get high-impact maintenance insights.

    Convenience endpoint for prioritizing actionable insights.
    """
    try:
        df = retrieve_maintenance_insights(
            impact_level="HIGH",
            limit=limit,
            location_id=location_id,
        )
        
        if df.empty:
            return []
        
        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve high-impact insights: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# SUMMARY & STATISTICS ENDPOINTS
# ============================================================================

@router.get(
    "/summary",
    response_model=PredictionSummary,
    summary="Get prediction summary statistics",
    description="Get overview statistics for all predictions and suggestions"
)
async def get_prediction_summary(
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> Dict[str, Any]:
    """
    Get summary statistics for predictions using direct SQL aggregations.
    """
    try:
        from .neon import get_conn as _get_conn
        conn = _get_conn()
        cur = conn.cursor()
        loc = [location_id] if location_id is not None else []
        loc_filter = "AND location_id = %s" if location_id is not None else ""

        # Single query: count latest prediction per asset by risk level
        cur.execute(f"""
            SELECT
                COUNT(*) AS total_assets,
                COUNT(CASE WHEN risk_level='CRITICAL' THEN 1 END) AS critical_risk,
                COUNT(CASE WHEN risk_level='HIGH' THEN 1 END) AS high_risk
            FROM (
                SELECT DISTINCT ON (asset_id) asset_id, risk_level
                FROM asset_failure_predictions WHERE 1=1 {loc_filter}
                ORDER BY asset_id, prediction_date DESC
            ) latest
        """, loc)
        row = cur.fetchone()
        total_assets  = row['total_assets']  or 0
        critical_risk = row['critical_risk'] or 0
        high_risk     = row['high_risk']     or 0

        # Single query: pending suggestions total savings + count
        cur.execute(f"""
            SELECT COALESCE(SUM(estimated_cost_savings), 0) AS total_savings,
                   COUNT(*) AS pending_count
            FROM pm_optimization_suggestions
            WHERE status='pending' {loc_filter}
        """, loc)
        row2 = cur.fetchone()

        # Single query: insight count
        cur.execute(f"SELECT COUNT(*) AS cnt FROM maintenance_insights WHERE 1=1 {loc_filter}", loc)
        insight_count = cur.fetchone()['cnt'] or 0

        conn.close()
        return {
            "total_assets_monitored": total_assets,
            "high_risk_assets": high_risk,
            "critical_risk_assets": critical_risk,
            "total_cost_savings_potential": round(float(row2['total_savings']), 2),
            "pending_suggestions": row2['pending_count'] or 0,
            "latest_insights": insight_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")


@router.get(
    "/dashboard",
    summary="Get dashboard data",
    description="Get comprehensive data for prediction dashboard (all endpoints combined)"
)
async def get_prediction_dashboard(
    location_id: Optional[int] = Query(
        None,
        description="Filter by location ID"
    ),
) -> Dict[str, Any]:
    """
    Get dashboard data using direct SQL — no pandas, single connection.
    """
    try:
        from .neon import get_conn as _get_conn
        conn = _get_conn()
        cur = conn.cursor()
        loc = [location_id] if location_id is not None else []
        loc_filter = "AND location_id = %s" if location_id is not None else ""

        # Summary counts
        cur.execute(f"""
            SELECT
                COUNT(*) AS total_assets,
                COUNT(CASE WHEN risk_level='CRITICAL' THEN 1 END) AS critical_risk,
                COUNT(CASE WHEN risk_level='HIGH' THEN 1 END) AS high_risk
            FROM (
                SELECT DISTINCT ON (asset_id) asset_id, risk_level
                FROM asset_failure_predictions WHERE 1=1 {loc_filter}
                ORDER BY asset_id, prediction_date DESC
            ) latest
        """, loc)
        s = cur.fetchone()

        # Top 10 high-risk assets
        cur.execute(f"""
            SELECT DISTINCT ON (asset_id) asset_id, risk_level, failure_probability,
                   days_to_predicted_failure, recommendation
            FROM asset_failure_predictions WHERE failure_probability >= 0.5 {loc_filter}
            ORDER BY asset_id, prediction_date DESC, failure_probability DESC
            LIMIT 10
        """, loc)
        high_risk = [dict(r) for r in cur.fetchall()]

        # Top 10 cost saving opportunities
        cur.execute(f"""
            SELECT asset_id, estimated_cost_savings, current_pm_frequency_days,
                   suggested_pm_frequency_days, reason
            FROM pm_optimization_suggestions
            WHERE status='pending' AND estimated_cost_savings >= 50 {loc_filter}
            ORDER BY estimated_cost_savings DESC LIMIT 10
        """, loc)
        cost_savings = [dict(r) for r in cur.fetchall()]

        # Latest 5 insights
        cur.execute(f"""
            SELECT title, description, insight_type, impact_level,
                   confidence_score, affected_assets, insight_date
            FROM maintenance_insights WHERE 1=1 {loc_filter}
            ORDER BY insight_date DESC LIMIT 5
        """, loc)
        insights = [dict(r) for r in cur.fetchall()]

        conn.close()
        return {
            "summary": {
                "total_assets_monitored": s['total_assets'] or 0,
                "high_risk_assets": s['high_risk'] or 0,
                "critical_risk_assets": s['critical_risk'] or 0,
            },
            "high_risk_assets": high_risk,
            "cost_saving_opportunities": cost_savings,
            "latest_insights": insights,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# STANDALONE APP (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    """
    Run prediction API as standalone service.
    
    For production, integrate routes into main api.py
    """
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI(
        title="Maintenance Analytics Prediction API",
        description="API for accessing asset failure predictions, PM optimizations, and insights",
        version="1.0.0"
    )
    
    # Include prediction routes
    app.include_router(router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Maintenance Analytics Prediction API",
            "version": "1.0.0",
            "endpoints": {
                "failure_predictions": "/predictions/failures",
                "high_risk_assets": "/predictions/failures/high-risk",
                "pm_optimizations": "/predictions/pm-optimization",
                "cost_savings": "/predictions/pm-optimization/cost-savings",
                "insights": "/predictions/insights",
                "summary": "/predictions/summary",
                "dashboard": "/predictions/dashboard"
            }
        }
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    print("Starting Prediction API...")
    print("API Docs: http://localhost:8001/docs")
    print("Dashboard: http://localhost:8001/predictions/dashboard")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True
    )