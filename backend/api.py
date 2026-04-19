"""
Read-only FastAPI service for maintenance analytics KPIs.

This module provides REST API endpoints to retrieve calculated KPIs
from the SQLite database.

Run with: uvicorn backend.api:app --reload
"""

from dotenv import load_dotenv
load_dotenv()

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# Import database utilities
from .db import (
    get_daily_kpis,
    get_weekly_kpis,
    get_monthly_kpis,
    table_exists,
    DatabaseError
)
# Add this with your other imports
from .api_predictions import router as predictions_router
from .api_auth import router as auth_router
from .api_settings import router as settings_router
from .api_reports import router as reports_router
from .api_invites import router as invites_router

# Pydantic models for API responses
class KPIRecord(BaseModel):
    """Base model for KPI records."""
    id: Optional[int] = None
    kpi_name: str
    raw_value: Optional[float]
    truesignal_value: Optional[float]  # ← FIXED: was true_signal_value
    distortion_flag: bool  # ← FIXED: was distortion
    explanation_text: Optional[str] = None  # ← FIXED: was explanation
    created_at: Optional[str] = None


class DailyKPIRecord(KPIRecord):
    """Model for daily KPI records."""
    period_date: str


class WeeklyKPIRecord(KPIRecord):
    """Model for weekly KPI records."""
    period_week: str


class MonthlyKPIRecord(KPIRecord):
    """Model for monthly KPI records."""
    period_month: str


# Initialize FastAPI app
app = FastAPI(
    title="Maintenance Analytics KPI API",
    description="Read-only API for accessing calculated maintenance KPIs",
    version="1.0.0"
)

# ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include prediction routes
app.include_router(predictions_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(reports_router)
app.include_router(invites_router)

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.
    
    Returns:
        API metadata and available endpoints
    """
    return {
        "name": "Maintenance Analytics KPI API",
        "version": "1.0.0",
        "endpoints": {
            "daily_kpis": "/kpis/daily",
            "weekly_kpis": "/kpis/weekly",
            "monthly_kpis": "/kpis/monthly"
        },
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Service health status
    """
    try:
        # Check if database tables exist
        tables_ok = all([
            table_exists("daily_kpis"),
            table_exists("weekly_kpis"),
            table_exists("monthly_kpis")
        ])
        
        if tables_ok:
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "degraded", "database": "missing tables"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get(
    "/kpis/daily",
    response_model=List[DailyKPIRecord],
    tags=["KPIs"],
    summary="Get daily KPIs",
    description="Retrieve daily KPI records with optional filtering"
)
async def get_daily_kpis_endpoint(
    kpi_name: Optional[str] = Query(
        None,
        description="Filter by specific KPI name"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return"
    ),
    days: Optional[int] = Query(
        None,
        ge=1,
        description="Only return records from the last N days"
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve daily KPIs.

    Args:
        kpi_name: Optional filter by KPI name
        limit: Maximum records to return (1-1000, default 100)
        days: Optional number of days to look back

    Returns:
        List of daily KPI records

    Raises:
        HTTPException: If query fails or table doesn't exist
    """
    try:
        # Check if table exists
        if not table_exists("daily_kpis"):
            raise HTTPException(
                status_code=503,
                detail="Daily KPIs table not found. Run pipeline to generate KPIs."
            )

        # Query database
        results = get_daily_kpis(kpi_name=kpi_name, limit=limit, days=days)
        
        # Return empty list if no results (not an error)
        if not results:
            return []
        
        return results
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/kpis/weekly",
    response_model=List[WeeklyKPIRecord],
    tags=["KPIs"],
    summary="Get weekly KPIs",
    description="Retrieve weekly KPI records with optional filtering"
)
async def get_weekly_kpis_endpoint(
    kpi_name: Optional[str] = Query(
        None,
        description="Filter by specific KPI name"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return"
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve weekly KPIs.
    
    Args:
        kpi_name: Optional filter by KPI name
        limit: Maximum records to return (1-1000, default 100)
        
    Returns:
        List of weekly KPI records
        
    Raises:
        HTTPException: If query fails or table doesn't exist
    """
    try:
        # Check if table exists
        if not table_exists("weekly_kpis"):
            raise HTTPException(
                status_code=503,
                detail="Weekly KPIs table not found. Run pipeline to generate KPIs."
            )
        
        # Query database
        results = get_weekly_kpis(kpi_name=kpi_name, limit=limit)
        
        # Return empty list if no results (not an error)
        if not results:
            return []
        
        return results
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/kpis/monthly",
    response_model=List[MonthlyKPIRecord],
    tags=["KPIs"],
    summary="Get monthly KPIs",
    description="Retrieve monthly KPI records with optional filtering"
)
async def get_monthly_kpis_endpoint(
    kpi_name: Optional[str] = Query(
        None,
        description="Filter by specific KPI name"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return"
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve monthly KPIs.
    
    Args:
        kpi_name: Optional filter by KPI name
        limit: Maximum records to return (1-1000, default 100)
        
    Returns:
        List of monthly KPI records
        
    Raises:
        HTTPException: If query fails or table doesn't exist
    """
    try:
        # Check if table exists
        if not table_exists("monthly_kpis"):
            raise HTTPException(
                status_code=503,
                detail="Monthly KPIs table not found. Run pipeline to generate KPIs."
            )
        
        # Query database
        results = get_monthly_kpis(kpi_name=kpi_name, limit=limit)
        
        # Return empty list if no results (not an error)
        if not results:
            return []
        
        return results
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Maintenance Analytics KPI API...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print()
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )