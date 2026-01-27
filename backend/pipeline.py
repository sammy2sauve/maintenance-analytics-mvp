"""
End-to-end KPI pipeline for maintenance analytics MVP.

This module orchestrates the complete KPI calculation workflow:
1. Load and clean work order data
2. Calculate daily, weekly, and monthly KPIs
3. Store results in SQLite database

Run as a script: python backend/pipeline.py
"""

import sys
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import pandas as pd

# Import project modules
try:
    from load_and_map_data import load_and_prepare_data, DataLoadError
    from calculate_kpis import calculate_all, KPICalculationError
    from kpi_storage import (
        create_kpi_tables,
        store_daily_kpis,
        store_weekly_kpis,
        store_monthly_kpis,
        KPIStorageError
    )
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Make sure all backend modules are in the same directory")
    sys.exit(1)


class PipelineError(Exception):
    """Custom exception for pipeline execution errors."""
    pass


def log_step(step_name: str, status: str = "START", details: str = "") -> None:
    """
    Log pipeline step progress with timestamp.
    
    Args:
        step_name: Name of the pipeline step
        status: Status indicator (START, SUCCESS, ERROR)
        details: Additional details to log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    symbols = {
        "START": "▶",
        "SUCCESS": "✓",
        "ERROR": "✗",
        "INFO": "ℹ"
    }
    symbol = symbols.get(status, "•")
    
    message = f"[{timestamp}] {symbol} {step_name}"
    if details:
        message += f": {details}"
    
    print(message)


def load_data() -> pd.DataFrame:
    """
    Load and prepare work order data.
    
    Returns:
        Cleaned DataFrame ready for KPI calculations
        
    Raises:
        PipelineError: If data loading fails
    """
    log_step("LOAD DATA", "START")
    
    try:
        df = load_and_prepare_data()
        
        if df.empty:
            raise PipelineError("Loaded DataFrame is empty")
        
        log_step("LOAD DATA", "SUCCESS", f"Loaded {len(df)} work orders")
        return df
        
    except DataLoadError as e:
        log_step("LOAD DATA", "ERROR", str(e))
        raise PipelineError(f"Data loading failed: {str(e)}")
    except Exception as e:
        log_step("LOAD DATA", "ERROR", str(e))
        raise PipelineError(f"Unexpected error during data load: {str(e)}")


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all KPIs (daily, weekly, monthly).
    
    Args:
        df: Cleaned work orders DataFrame
        
    Returns:
        DataFrame with all calculated KPIs
        
    Raises:
        PipelineError: If KPI calculation fails
    """
    log_step("CALCULATE KPIs", "START")
    
    try:
        kpi_results = calculate_all(df)
        
        if kpi_results.empty:
            raise PipelineError("KPI calculation returned empty results")
        
        # Count distortions
        distortion_count = kpi_results['distortion_flag'].sum()
        total_kpis = len(kpi_results)
        
        log_step("CALCULATE KPIs", "SUCCESS", 
                f"Calculated {total_kpis} KPIs ({distortion_count} distortions detected)")
        
        return kpi_results
        
    except KPICalculationError as e:
        log_step("CALCULATE KPIs", "ERROR", str(e))
        raise PipelineError(f"KPI calculation failed: {str(e)}")
    except Exception as e:
        log_step("CALCULATE KPIs", "ERROR", str(e))
        raise PipelineError(f"Unexpected error during KPI calculation: {str(e)}")


def categorize_kpis(kpi_results: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Categorize KPIs into daily, weekly, and monthly DataFrames.
    
    Args:
        kpi_results: Combined KPI results DataFrame
        
    Returns:
        Tuple of (daily_kpis, weekly_kpis, monthly_kpis) DataFrames
    """
    log_step("CATEGORIZE KPIs", "START")
    
    # Define KPI categories
    daily_kpi_names = [
        'Reactive Work Ratio',
        'PM Compliance (True)',
        'Work Order Backlog Age',
        'Schedule Adherence',
        'Emergency Work %'
    ]
    
    weekly_kpi_names = [
        'PM Slippage Rate',
        'Reactive Creep Index',
        'Mean Time to Complete (True MTTC)',
        'Labor Utilization (Actual vs Logged)'
    ]
    
    monthly_kpi_names = [
        'PM Effectiveness Score',
        'Backlog Growth Rate',
        'Failure Recurrence Index',
        'Maintenance Load Stability'
    ]
    
    # Filter by KPI name
    daily_kpis = kpi_results[kpi_results['kpi_name'].isin(daily_kpi_names)].copy()
    weekly_kpis = kpi_results[kpi_results['kpi_name'].isin(weekly_kpi_names)].copy()
    monthly_kpis = kpi_results[kpi_results['kpi_name'].isin(monthly_kpi_names)].copy()
    
    log_step("CATEGORIZE KPIs", "SUCCESS", 
            f"Daily: {len(daily_kpis)}, Weekly: {len(weekly_kpis)}, Monthly: {len(monthly_kpis)}")
    
    return daily_kpis, weekly_kpis, monthly_kpis


def setup_database() -> None:
    """
    Initialize database tables for KPI storage.
    
    Raises:
        PipelineError: If table creation fails
    """
    log_step("SETUP DATABASE", "START")
    
    try:
        create_kpi_tables()
        log_step("SETUP DATABASE", "SUCCESS", "KPI tables ready")
        
    except KPIStorageError as e:
        log_step("SETUP DATABASE", "ERROR", str(e))
        raise PipelineError(f"Database setup failed: {str(e)}")
    except Exception as e:
        log_step("SETUP DATABASE", "ERROR", str(e))
        raise PipelineError(f"Unexpected error during database setup: {str(e)}")


def store_kpis(
    daily_kpis: pd.DataFrame,
    weekly_kpis: pd.DataFrame,
    monthly_kpis: pd.DataFrame
) -> Tuple[int, int, int]:
    """
    Store KPIs to database.
    
    Args:
        daily_kpis: Daily KPIs DataFrame
        weekly_kpis: Weekly KPIs DataFrame
        monthly_kpis: Monthly KPIs DataFrame
        
    Returns:
        Tuple of (daily_rows, weekly_rows, monthly_rows) stored
        
    Raises:
        PipelineError: If storage fails
    """
    log_step("STORE KPIs", "START")
    
    daily_rows = 0
    weekly_rows = 0
    monthly_rows = 0
    
    try:
        # Store daily KPIs
        if not daily_kpis.empty:
            daily_rows = store_daily_kpis(daily_kpis)
            log_step("STORE KPIs", "INFO", f"Stored {daily_rows} daily KPI records")
        
        # Store weekly KPIs
        if not weekly_kpis.empty:
            weekly_rows = store_weekly_kpis(weekly_kpis)
            log_step("STORE KPIs", "INFO", f"Stored {weekly_rows} weekly KPI records")
        
        # Store monthly KPIs
        if not monthly_kpis.empty:
            monthly_rows = store_monthly_kpis(monthly_kpis)
            log_step("STORE KPIs", "INFO", f"Stored {monthly_rows} monthly KPI records")
        
        total_rows = daily_rows + weekly_rows + monthly_rows
        log_step("STORE KPIs", "SUCCESS", f"Stored {total_rows} total KPI records")
        
        return daily_rows, weekly_rows, monthly_rows
        
    except KPIStorageError as e:
        log_step("STORE KPIs", "ERROR", str(e))
        raise PipelineError(f"KPI storage failed: {str(e)}")
    except Exception as e:
        log_step("STORE KPIs", "ERROR", str(e))
        raise PipelineError(f"Unexpected error during KPI storage: {str(e)}")
    
def run_pipeline(verbose: bool = True) -> dict:
    """
    Execute the complete KPI calculation and storage pipeline.
    
    Pipeline stages:
    1. Setup database tables
    2. Load and clean work order data
    3. Calculate all KPIs
    4. Categorize KPIs by period (daily/weekly/monthly)
    5. Store KPIs in database
    
    Args:
        verbose: If True, print detailed progress logs
        
    Returns:
        Dictionary with pipeline execution results and statistics
        
    Raises:
        PipelineError: If any pipeline stage fails
    """
    start_time = datetime.now()
    
    if verbose:
        print("=" * 70)
        print("MAINTENANCE ANALYTICS KPI PIPELINE")
        print("=" * 70)
        print()
    
    results = {
        'success': False,
        'start_time': start_time,
        'end_time': None,
        'duration_seconds': None,
        'work_orders_processed': 0,
        'kpis_calculated': 0,
        'kpis_stored': 0,
        'distortions_detected': 0,
        'error': None
    }
    
    try:
        # Stage 1: Setup database
        setup_database()
        
        # Stage 2: Load data
        df = load_data()
        results['work_orders_processed'] = len(df)
        
        # Stage 3: Calculate KPIs
        kpi_results = calculate_kpis(df)
        results['kpis_calculated'] = len(kpi_results)
        results['distortions_detected'] = int(kpi_results['distortion_flag'].sum())
        
        # Stage 4: Categorize KPIs
        daily_kpis, weekly_kpis, monthly_kpis = categorize_kpis(kpi_results)
        
        # Stage 5: Store KPIs
        daily_rows, weekly_rows, monthly_rows = store_kpis(
            daily_kpis, weekly_kpis, monthly_kpis
        )
        results['kpis_stored'] = daily_rows + weekly_rows + monthly_rows
        
        # Mark success
        results['success'] = True
        
        if verbose:
            print()
            print("=" * 70)
            print("PIPELINE COMPLETED SUCCESSFULLY")
            print("=" * 70)
        
    except PipelineError as e:
        results['error'] = str(e)
        if verbose:
            print()
            print("=" * 70)
            print("PIPELINE FAILED")
            print("=" * 70)
            print(f"Error: {e}")
        raise
        
    except Exception as e:
        results['error'] = f"Unexpected error: {str(e)}"
        if verbose:
            print()
            print("=" * 70)
            print("PIPELINE FAILED")
            print("=" * 70)
            print(f"Unexpected error: {e}")
        raise PipelineError(f"Pipeline execution failed: {str(e)}")
        
    finally:
        end_time = datetime.now()
        results['end_time'] = end_time
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        if verbose:
            print_summary(results)
    
    return results


def print_summary(results: dict) -> None:
    """
    Print pipeline execution summary.
    
    Args:
        results: Dictionary with pipeline execution results
    """
    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Status: {'SUCCESS ✓' if results['success'] else 'FAILED ✗'}")
    print(f"Duration: {results['duration_seconds']:.2f} seconds")
    print()
    print("Metrics:")
    print(f"  • Work orders processed: {results['work_orders_processed']}")
    print(f"  • KPIs calculated: {results['kpis_calculated']}")
    print(f"  • KPIs stored: {results['kpis_stored']}")
    print(f"  • Distortions detected: {results['distortions_detected']}")
    
    if results['error']:
        print()
        print(f"Error: {results['error']}")
    
    print("=" * 70)


def main() -> int:
    """
    Main entry point for pipeline script.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        results = run_pipeline(verbose=True)
        return 0 if results['success'] else 1
        
    except PipelineError as e:
        # Error already logged by run_pipeline
        return 1
        
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        return 1


if __name__ == "__main__":
    """
    Run pipeline when executed as a script.
    
    Usage:
        python backend/pipeline.py
    """
    exit_code = main()
    sys.exit(exit_code)