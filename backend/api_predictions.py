"""
Prediction API endpoints for maintenance analytics MVP.

This module provides REST API endpoints for accessing failure predictions,
PM optimization suggestions, and maintenance insights.

These endpoints can be integrated into the main API or run standalone.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
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
    prediction_date: str
    failure_probability: float = Field(..., ge=0, le=1)
    confidence_score: float = Field(..., ge=0, le=1)
    days_to_predicted_failure: Optional[int] = None
    mtbf_days: Optional[float] = None
    days_since_last_pm: Optional[int] = None
    reactive_work_count_90d: Optional[int] = None
    risk_level: str
    recommendation: str
    created_at: Optional[str] = None


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
    suggestion_date: str
    status: str = "pending"
    created_at: Optional[str] = None


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
    insight_date: str
    created_at: Optional[str] = None


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
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve asset failure predictions.

    Returns predictions sorted by failure probability (highest risk first).
    """
    try:
        df = retrieve_failure_predictions(
            asset_id=asset_id,
            risk_level=risk_level,
            min_probability=min_probability,
            limit=limit
        )

        if df.empty:
            return []

        if days and 'prediction_date' in df.columns:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            df = df[df['prediction_date'] >= cutoff]

        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve failure predictions: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


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
    )
) -> List[Dict[str, Any]]:
    """
    Get assets with high failure risk.
    
    Convenience endpoint for monitoring critical assets.
    """
    try:
        df = get_high_risk_assets(
            min_probability=min_probability,
            limit=limit
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
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve PM optimization suggestions.
    
    Returns suggestions sorted by cost savings (highest first).
    """
    try:
        df = retrieve_pm_optimization_suggestions(
            asset_id=asset_id,
            status=status,
            min_savings=min_savings,
            limit=limit
        )
        
        if df.empty:
            return []
        
        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve PM suggestions: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


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
    )
) -> List[Dict[str, Any]]:
    """
    Get cost-saving opportunities.
    
    Convenience endpoint for identifying top savings opportunities.
    """
    try:
        df = get_cost_saving_opportunities(
            min_savings=min_savings,
            limit=limit
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
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve maintenance insights.
    
    Returns insights sorted by date and confidence score.
    """
    try:
        df = retrieve_maintenance_insights(
            insight_type=insight_type,
            impact_level=impact_level,
            limit=limit
        )
        
        if df.empty:
            return []
        
        return _clean_records(df.to_dict('records'))
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve insights: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


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
    )
) -> List[Dict[str, Any]]:
    """
    Get high-impact maintenance insights.
    
    Convenience endpoint for prioritizing actionable insights.
    """
    try:
        df = retrieve_maintenance_insights(
            impact_level="HIGH",
            limit=limit
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
async def get_prediction_summary() -> Dict[str, Any]:
    """
    Get summary statistics for predictions.
    
    Provides a high-level overview of:
    - Total assets monitored
    - High-risk asset count
    - Critical risk asset count
    - Total cost savings potential
    - Pending suggestions count
    - Latest insights count
    """
    try:
        # Get all predictions
        all_predictions = retrieve_failure_predictions(limit=10000)
        
        # Count by risk level
        total_assets = len(all_predictions)
        high_risk = len(all_predictions[all_predictions['risk_level'] == 'HIGH'])
        critical_risk = len(all_predictions[all_predictions['risk_level'] == 'CRITICAL'])
        
        # Get all pending suggestions
        pending_suggestions = retrieve_pm_optimization_suggestions(
            status='pending',
            limit=10000
        )
        
        # Calculate total savings potential
        total_savings = 0.0
        if not pending_suggestions.empty:
            total_savings = pending_suggestions['estimated_cost_savings'].sum()
        
        # Get recent insights
        recent_insights = retrieve_maintenance_insights(limit=10000)
        
        return {
            "total_assets_monitored": total_assets,
            "high_risk_assets": high_risk,
            "critical_risk_assets": critical_risk,
            "total_cost_savings_potential": round(total_savings, 2),
            "pending_suggestions": len(pending_suggestions),
            "latest_insights": len(recent_insights)
        }
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/dashboard",
    summary="Get dashboard data",
    description="Get comprehensive data for prediction dashboard (all endpoints combined)"
)
async def get_prediction_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive prediction dashboard data.
    
    Returns a single response with:
    - Summary statistics
    - Top 10 high-risk assets
    - Top 10 cost-saving opportunities
    - Latest 5 insights
    """
    try:
        # Get summary
        summary = await get_prediction_summary()
        
        # Get high-risk assets
        high_risk_df = get_high_risk_assets(min_probability=0.5, limit=10)
        high_risk = _clean_records(high_risk_df.to_dict('records')) if not high_risk_df.empty else []
        
        # Get cost savings
        savings_df = get_cost_saving_opportunities(min_savings=50, limit=10)
        cost_savings = _clean_records(savings_df.to_dict('records')) if not savings_df.empty else []
        
        # Get insights
        insights_df = retrieve_maintenance_insights(limit=5)
        insights = _clean_records(insights_df.to_dict('records')) if not insights_df.empty else []
        
        return {
            "summary": summary,
            "high_risk_assets": high_risk,
            "cost_saving_opportunities": cost_savings,
            "latest_insights": insights
        }
        
    except PredictionStorageError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )
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