"""
KPI calculation module for maintenance analytics MVP.

This module implements 13 maintenance KPIs across daily, weekly, and monthly
time horizons, calculating both raw CMMS values and TrueSignal corrected values.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class KPICalculationError(Exception):
    """Custom exception for KPI calculation errors."""
    pass


def _safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero
        
    Returns:
        Result of division or default value
    """
    return numerator / denominator if denominator != 0 else default


def _calculate_distortion(raw: float, truesignal: float, threshold: float = 0.1) -> bool:
    """
    Determine if there's significant distortion between raw and TrueSignal values.
    
    Args:
        raw: Raw CMMS value
        truesignal: TrueSignal corrected value
        threshold: Percentage threshold for distortion (default 10%)
        
    Returns:
        True if distortion exceeds threshold
    """
    if raw == 0 and truesignal == 0:
        return False
    if raw == 0:
        return True
    
    distortion_pct = abs(truesignal - raw) / abs(raw)
    return distortion_pct > threshold


# ============================================================================
# DAILY KPIs
# ============================================================================

def calculate_reactive_work_ratio(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Reactive Work Ratio (Daily KPI #1).
    
    Ratio of reactive work orders to total work orders.
    Raw: All reactive work / all work
    TrueSignal: Only completed reactive / only completed work
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with kpi_name, raw_value, truesignal_value, distortion_flag, explanation
    """
    try:
        # Raw calculation: all reactive vs all work
        reactive_count = len(df[df['type'].str.lower().str.contains('reactive', na=False)])
        total_count = len(df)
        raw_value = _safe_division(reactive_count, total_count)
        
        # TrueSignal: only completed work orders
        completed_df = df[df['status'].str.lower().str.contains('complet', na=False)]
        completed_reactive = len(completed_df[
            completed_df['type'].str.lower().str.contains('reactive', na=False)
        ])
        completed_total = len(completed_df)
        truesignal_value = _safe_division(completed_reactive, completed_total)
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw ratio includes all {reactive_count}/{total_count} work orders. "
            f"TrueSignal filters to completed work only ({completed_reactive}/{completed_total}), "
            f"removing scheduled/cancelled reactive work that inflates the metric."
        )
        
        return {
            'kpi_name': 'Reactive Work Ratio',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Reactive Work Ratio: {str(e)}")


def calculate_pm_compliance(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate PM Compliance (Daily KPI #2).
    
    Percentage of PM work orders completed on time.
    Raw: PM completed / PM scheduled
    TrueSignal: PM completed on-time / PM due
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Filter PM work orders
        pm_df = df[df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)]
        
        # Raw: completed vs scheduled
        pm_completed = len(pm_df[pm_df['status'].str.lower().str.contains('complet', na=False)])
        pm_scheduled = len(pm_df)
        raw_value = _safe_division(pm_completed, pm_scheduled)
        
        # TrueSignal: completed on-time vs due
        pm_completed_df = pm_df[pm_df['status'].str.lower().str.contains('complet', na=False)].copy()
        
        # Calculate on-time completion (completed before or on due date)
        pm_completed_df['on_time'] = (
            (pd.notna(pm_completed_df['completion_date'])) & 
            (pd.notna(pm_completed_df['due_date'])) &
            (pm_completed_df['completion_date'] <= pm_completed_df['due_date'])
        )
        
        pm_on_time = pm_completed_df['on_time'].sum()
        pm_due = len(pm_df[pd.notna(pm_df['due_date'])])
        truesignal_value = _safe_division(pm_on_time, pm_due)
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw compliance counts any PM completion ({pm_completed}/{pm_scheduled}). "
            f"TrueSignal measures on-time completion ({pm_on_time}/{pm_due}), "
            f"revealing late PM work masked by raw completion rates."
        )
        
        return {
            'kpi_name': 'PM Compliance (True)',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating PM Compliance: {str(e)}")


def calculate_backlog_age(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Work Order Backlog Age (Daily KPI #3).
    
    Average age of open work orders in days.
    Raw: Age of all open WOs from creation date
    TrueSignal: Age of open WOs from scheduled start date, excluding future-scheduled
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        current_date = pd.Timestamp.now()
        
        # Filter open work orders
        open_df = df[~df['status'].str.lower().str.contains('complet|cancel|close', na=False)].copy()
        
        # Raw: average age from creation date
        open_df['age_from_creation'] = (
            current_date - pd.to_datetime(open_df['creation_date'], errors='coerce')
        ).dt.days
        raw_value = open_df['age_from_creation'].mean() if len(open_df) > 0 else 0.0
        
        # TrueSignal: age from scheduled start, exclude future-scheduled
        open_df['scheduled_start_dt'] = pd.to_datetime(open_df['scheduled_start'], errors='coerce')
        past_due_df = open_df[open_df['scheduled_start_dt'] <= current_date]
        
        past_due_df['age_from_scheduled'] = (
            current_date - past_due_df['scheduled_start_dt']
        ).dt.days
        truesignal_value = past_due_df['age_from_scheduled'].mean() if len(past_due_df) > 0 else 0.0
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw backlog age averages {len(open_df)} open WOs from creation date ({raw_value:.1f} days). "
            f"TrueSignal uses {len(past_due_df)} past-due WOs from scheduled start ({truesignal_value:.1f} days), "
            f"excluding future-scheduled work that artificially inflates backlog age."
        )
        
        return {
            'kpi_name': 'Work Order Backlog Age',
            'raw_value': round(raw_value, 2),
            'truesignal_value': round(truesignal_value, 2),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Backlog Age: {str(e)}")


def calculate_schedule_adherence(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Schedule Adherence (Daily KPI #4).
    
    Percentage of work orders started on scheduled date.
    Raw: WOs with start date / total scheduled WOs
    TrueSignal: WOs started within tolerance window of scheduled start
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Filter to work orders with scheduled start dates
        scheduled_df = df[pd.notna(df['scheduled_start'])].copy()
        
        # Raw: any start date recorded
        started_count = scheduled_df[pd.notna(scheduled_df['start_date'])].shape[0]
        total_scheduled = len(scheduled_df)
        raw_value = _safe_division(started_count, total_scheduled)
        
        # TrueSignal: started within +/- 1 day of scheduled start
        scheduled_df['scheduled_start_dt'] = pd.to_datetime(scheduled_df['scheduled_start'], errors='coerce')
        scheduled_df['start_date_dt'] = pd.to_datetime(scheduled_df['start_date'], errors='coerce')
        
        started_df = scheduled_df[pd.notna(scheduled_df['start_date_dt'])].copy()
        started_df['days_diff'] = (
            started_df['start_date_dt'] - started_df['scheduled_start_dt']
        ).dt.days
        
        on_schedule_count = started_df[started_df['days_diff'].abs() <= 1].shape[0]
        truesignal_value = _safe_division(on_schedule_count, total_scheduled)
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw adherence counts {started_count}/{total_scheduled} WOs with any start date. "
            f"TrueSignal measures on-time starts ({on_schedule_count}/{total_scheduled}, ±1 day tolerance), "
            f"revealing schedule drift masked by eventual work completion."
        )
        
        return {
            'kpi_name': 'Schedule Adherence',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Schedule Adherence: {str(e)}")


def calculate_emergency_work_percentage(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Emergency Work Percentage (Daily KPI #5).
    
    Percentage of work orders classified as emergency.
    Raw: Emergency priority / all work
    TrueSignal: True emergency based on completion time and priority
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        total_count = len(df)
        
        # Raw: all work orders marked as emergency priority
        emergency_count = len(df[df['priority'].str.lower() == 'emergency'])
        raw_value = _safe_division(emergency_count, total_count)
        
        # TrueSignal: emergency priority + completed within 24 hours
        completed_df = df[df['status'].str.lower().str.contains('complet', na=False)].copy()
        completed_df['creation_dt'] = pd.to_datetime(completed_df['creation_date'], errors='coerce')
        completed_df['completion_dt'] = pd.to_datetime(completed_df['completion_date'], errors='coerce')
        
        completed_df['completion_time'] = (
            completed_df['completion_dt'] - completed_df['creation_dt']
        ).dt.total_seconds() / 3600  # hours
        
        true_emergency = completed_df[
            (completed_df['priority'].str.lower() == 'emergency') &
            (completed_df['completion_time'] <= 24) &
            (pd.notna(completed_df['completion_time']))
        ]
        
        true_emergency_count = len(true_emergency)
        completed_total = len(completed_df)
        truesignal_value = _safe_division(true_emergency_count, completed_total)
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw metric counts {emergency_count}/{total_count} WOs marked emergency. "
            f"TrueSignal identifies {true_emergency_count}/{completed_total} true emergencies "
            f"(completed within 24h), revealing priority inflation in CMMS data."
        )
        
        return {
            'kpi_name': 'Emergency Work %',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Emergency Work %: {str(e)}")
    # ============================================================================
# WEEKLY KPIs
# ============================================================================

def calculate_pm_slippage_rate(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate PM Slippage Rate (Weekly KPI #1).
    
    Rate at which PM work orders are delayed beyond scheduled date.
    Raw: PM WOs past due / total PM
    TrueSignal: PM delay days / total PM days scheduled (weighted by delay severity)
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Filter PM work orders
        pm_df = df[df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)].copy()
        pm_df['scheduled_start_dt'] = pd.to_datetime(pm_df['scheduled_start'], errors='coerce')
        pm_df['completion_dt'] = pd.to_datetime(pm_df['completion_date'], errors='coerce')
        
        current_date = pd.Timestamp.now()
        
        # Raw: percentage of PM past due date
        pm_with_schedule = pm_df[pd.notna(pm_df['scheduled_start_dt'])]
        past_due_pm = pm_with_schedule[
            (pm_with_schedule['scheduled_start_dt'] < current_date) &
            (~pm_with_schedule['status'].str.lower().str.contains('complet', na=False))
        ]
        
        raw_value = _safe_division(len(past_due_pm), len(pm_with_schedule))
        
        # TrueSignal: weighted slippage based on delay days
        completed_pm = pm_df[
            (pd.notna(pm_df['completion_dt'])) & 
            (pd.notna(pm_df['scheduled_start_dt']))
        ].copy()
        
        completed_pm['delay_days'] = (
            completed_pm['completion_dt'] - completed_pm['scheduled_start_dt']
        ).dt.days
        
        completed_pm['delay_days'] = completed_pm['delay_days'].clip(lower=0)  # Only positive delays
        total_delay_days = completed_pm['delay_days'].sum()
        total_pm_count = len(completed_pm)
        
        truesignal_value = _safe_division(total_delay_days, total_pm_count) / 7  # Normalize to weeks
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw slippage shows {len(past_due_pm)}/{len(pm_with_schedule)} PM WOs past due ({raw_value:.2%}). "
            f"TrueSignal calculates average delay of {truesignal_value:.2f} weeks across {total_pm_count} completed PMs, "
            f"revealing severity of delays beyond binary past-due status."
        )
        
        return {
            'kpi_name': 'PM Slippage Rate',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating PM Slippage Rate: {str(e)}")


def calculate_reactive_creep_index(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Reactive Creep Index (Weekly KPI #2).
    
    Measures increasing reactive work following PM work.
    Raw: Reactive work count trend
    TrueSignal: Reactive work within 7 days of PM on same asset (indicates PM ineffectiveness)
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Raw: simple reactive work percentage
        reactive_df = df[df['type'].str.lower().str.contains('reactive', na=False)]
        total_work = len(df)
        raw_value = _safe_division(len(reactive_df), total_work)
        
        # TrueSignal: reactive work within 7 days after PM on same asset
        pm_df = df[
            (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
            (df['status'].str.lower().str.contains('complet', na=False))
        ].copy()
        
        pm_df['completion_dt'] = pd.to_datetime(pm_df['completion_date'], errors='coerce')
        
        reactive_completed = reactive_df[
            reactive_df['status'].str.lower().str.contains('complet', na=False)
        ].copy()
        reactive_completed['creation_dt'] = pd.to_datetime(reactive_completed['creation_date'], errors='coerce')
        
        # Find reactive work within 7 days of PM completion on same asset
        creep_count = 0
        for _, pm_row in pm_df.iterrows():
            if pd.notna(pm_row['completion_dt']) and pd.notna(pm_row['asset_id']):
                asset_reactive = reactive_completed[
                    (reactive_completed['asset_id'] == pm_row['asset_id']) &
                    (reactive_completed['creation_dt'] > pm_row['completion_dt']) &
                    (reactive_completed['creation_dt'] <= pm_row['completion_dt'] + pd.Timedelta(days=7))
                ]
                creep_count += len(asset_reactive)
        
        truesignal_value = _safe_division(creep_count, len(pm_df))
        
        distortion = _calculate_distortion(raw_value, truesignal_value, threshold=0.05)
        
        explanation = (
            f"Raw reactive work ratio is {raw_value:.2%} of all work. "
            f"TrueSignal identifies {creep_count} reactive WOs within 7 days of {len(pm_df)} PM completions "
            f"({truesignal_value:.2f} per PM), indicating PM effectiveness issues."
        )
        
        return {
            'kpi_name': 'Reactive Creep Index',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Reactive Creep Index: {str(e)}")


def calculate_mean_time_to_complete(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Mean Time to Complete - True MTTC (Weekly KPI #3).
    
    Average time from work order creation to completion.
    Raw: Completion date - creation date for all completed WOs
    TrueSignal: Actual work time excluding wait time (using start date)
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        completed_df = df[df['status'].str.lower().str.contains('complet', na=False)].copy()
        completed_df['creation_dt'] = pd.to_datetime(completed_df['creation_date'], errors='coerce')
        completed_df['start_dt'] = pd.to_datetime(completed_df['start_date'], errors='coerce')
        completed_df['completion_dt'] = pd.to_datetime(completed_df['completion_date'], errors='coerce')
        
        # Raw: creation to completion
        valid_raw = completed_df[
            (pd.notna(completed_df['creation_dt'])) & 
            (pd.notna(completed_df['completion_dt']))
        ].copy()
        
        valid_raw['total_time'] = (
            valid_raw['completion_dt'] - valid_raw['creation_dt']
        ).dt.total_seconds() / 3600  # hours
        
        raw_value = valid_raw['total_time'].mean() if len(valid_raw) > 0 else 0.0
        
        # TrueSignal: start to completion (actual work time)
        valid_true = completed_df[
            (pd.notna(completed_df['start_dt'])) & 
            (pd.notna(completed_df['completion_dt']))
        ].copy()
        
        valid_true['work_time'] = (
            valid_true['completion_dt'] - valid_true['start_dt']
        ).dt.total_seconds() / 3600  # hours
        
        truesignal_value = valid_true['work_time'].mean() if len(valid_true) > 0 else 0.0
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw MTTC averages {raw_value:.1f} hours from creation to completion ({len(valid_raw)} WOs). "
            f"TrueSignal measures {truesignal_value:.1f} hours of actual work time ({len(valid_true)} WOs), "
            f"excluding backlog wait time that inflates the metric."
        )
        
        return {
            'kpi_name': 'Mean Time to Complete (True MTTC)',
            'raw_value': round(raw_value, 2),
            'truesignal_value': round(truesignal_value, 2),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating MTTC: {str(e)}")


def calculate_labor_utilization(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Labor Utilization (Weekly KPI #4).
    
    Actual labor hours vs scheduled/planned hours.
    Raw: Actual hours / scheduled hours (can exceed 100%)
    TrueSignal: Actual hours / scheduled hours, capped at 100% to reveal over-logging
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Filter to completed work orders with labor data
        labor_df = df[
            (df['status'].str.lower().str.contains('complet', na=False)) &
            (pd.notna(df['labor_hours_scheduled'])) &
            (pd.notna(df['labor_hours_actual'])) &
            (df['labor_hours_scheduled'] > 0)
        ].copy()
        
        total_scheduled = labor_df['labor_hours_scheduled'].sum()
        total_actual = labor_df['labor_hours_actual'].sum()
        
        # Raw: simple ratio (can exceed 100%)
        raw_value = _safe_division(total_actual, total_scheduled)
        
        # TrueSignal: identify realistic utilization, flag over-logged hours
        labor_df['utilization'] = labor_df['labor_hours_actual'] / labor_df['labor_hours_scheduled']
        labor_df['capped_utilization'] = labor_df['utilization'].clip(upper=1.0)
        
        truesignal_value = labor_df['capped_utilization'].mean()
        
        over_logged_count = len(labor_df[labor_df['utilization'] > 1.0])
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw utilization shows {total_actual:.1f}/{total_scheduled:.1f} hours ({raw_value:.2%}). "
            f"TrueSignal caps at 100% per WO, revealing {over_logged_count}/{len(labor_df)} WOs with over-logged hours, "
            f"resulting in {truesignal_value:.2%} realistic utilization."
        )
        
        return {
            'kpi_name': 'Labor Utilization (Actual vs Logged)',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Labor Utilization: {str(e)}")
    # ============================================================================
# MONTHLY KPIs
# ============================================================================

def calculate_pm_effectiveness_score(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate PM Effectiveness Score (Monthly KPI #1).
    
    Measures how well PM prevents failures.
    Raw: PM completion rate
    TrueSignal: Reduction in reactive work on assets with completed PM
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Raw: PM completion percentage
        pm_df = df[df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)]
        pm_completed = len(pm_df[pm_df['status'].str.lower().str.contains('complet', na=False)])
        pm_total = len(pm_df)
        raw_value = _safe_division(pm_completed, pm_total)
        
        # TrueSignal: Compare reactive work on assets with/without recent PM
        pm_completed_df = df[
            (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
            (df['status'].str.lower().str.contains('complet', na=False))
        ].copy()
        
        pm_completed_df['completion_dt'] = pd.to_datetime(pm_completed_df['completion_date'], errors='coerce')
        
        # Get assets with PM in last 30 days
        current_date = pd.Timestamp.now()
        recent_pm_assets = set(pm_completed_df[
            (pm_completed_df['completion_dt'] >= current_date - pd.Timedelta(days=30))
        ]['asset_id'].dropna().unique())
        
        # Calculate reactive work ratio for assets with and without PM
        reactive_df = df[df['type'].str.lower().str.contains('reactive', na=False)]
        
        if len(recent_pm_assets) > 0:
            reactive_with_pm = len(reactive_df[reactive_df['asset_id'].isin(recent_pm_assets)])
            reactive_without_pm = len(reactive_df[~reactive_df['asset_id'].isin(recent_pm_assets)])
            
            assets_with_pm = len(recent_pm_assets)
            assets_without_pm = len(df['asset_id'].dropna().unique()) - assets_with_pm
            
            rate_with_pm = _safe_division(reactive_with_pm, assets_with_pm)
            rate_without_pm = _safe_division(reactive_without_pm, max(assets_without_pm, 1))
            
            # Effectiveness score: reduction in reactive work
            if rate_without_pm > 0:
                truesignal_value = max(0, 1 - (rate_with_pm / rate_without_pm))
            else:
                truesignal_value = 1.0 if rate_with_pm == 0 else 0.0
        else:
            truesignal_value = 0.0
        
        distortion = _calculate_distortion(raw_value, truesignal_value)
        
        explanation = (
            f"Raw PM effectiveness is {raw_value:.2%} completion rate ({pm_completed}/{pm_total}). "
            f"TrueSignal measures {truesignal_value:.2%} reduction in reactive work on {len(recent_pm_assets)} assets with recent PM, "
            f"revealing actual preventive impact."
        )
        
        return {
            'kpi_name': 'PM Effectiveness Score',
            'raw_value': round(raw_value, 4),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating PM Effectiveness Score: {str(e)}")


def calculate_backlog_growth_rate(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Backlog Growth Rate (Monthly KPI #2).
    
    Rate of change in work order backlog.
    Raw: Change in open WO count
    TrueSignal: Change in open WO count weighted by priority and age
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        current_date = pd.Timestamp.now()
        
        # Filter open work orders
        open_df = df[~df['status'].str.lower().str.contains('complet|cancel|close', na=False)].copy()
        
        # Raw: simple count change (simulate 30-day comparison)
        # For MVP, we'll use creation date to estimate trend
        open_df['creation_dt'] = pd.to_datetime(open_df['creation_date'], errors='coerce')
        
        recent_open = len(open_df[
            open_df['creation_dt'] >= current_date - pd.Timedelta(days=30)
        ])
        
        # Estimate completed in last 30 days
        completed_recent = len(df[
            (df['status'].str.lower().str.contains('complet', na=False)) &
            (pd.to_datetime(df['completion_date'], errors='coerce') >= current_date - pd.Timedelta(days=30))
        ])
        
        raw_value = recent_open - completed_recent  # Net change
        
        # TrueSignal: weighted by priority and age
        open_df['age_days'] = (current_date - open_df['creation_dt']).dt.days
        open_df['priority_weight'] = open_df['priority'].map({
            'emergency': 3.0,
            'high': 2.0,
            'normal': 1.0,
            'low': 0.5
        }).fillna(1.0)
        open_df['weighted_score'] = open_df['age_days'] * open_df['priority_weight']
        
        recent_weighted = open_df[
            open_df['creation_dt'] >= current_date - pd.Timedelta(days=30)
        ]['weighted_score'].sum()
        
        truesignal_value = recent_weighted / 30  # Average daily weighted growth
        
        distortion = abs(raw_value) > 10 or abs(truesignal_value) > 50
        
        explanation = (
            f"Raw backlog grew by {raw_value} WOs (net). "
            f"TrueSignal weighted growth is {truesignal_value:.1f} points/day, "
            f"accounting for {len(open_df)} open WOs with priority and age, revealing urgency of backlog growth."
        )
        
        return {
            'kpi_name': 'Backlog Growth Rate',
            'raw_value': round(raw_value, 2),
            'truesignal_value': round(truesignal_value, 2),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Backlog Growth Rate: {str(e)}")


def calculate_failure_recurrence_index(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Failure Recurrence Index (Monthly KPI #3).
    
    Measures repeat failures on same assets.
    Raw: Count of reactive work orders
    TrueSignal: Reactive WOs on assets with prior reactive work (within 90 days)
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Raw: total reactive work count
        reactive_df = df[df['type'].str.lower().str.contains('reactive', na=False)]
        raw_value = len(reactive_df)
        
        # TrueSignal: repeat reactive failures on same asset
        reactive_completed = reactive_df[
            reactive_df['status'].str.lower().str.contains('complet', na=False)
        ].copy()
        
        reactive_completed['completion_dt'] = pd.to_datetime(reactive_completed['completion_date'], errors='coerce')
        reactive_completed = reactive_completed.sort_values('completion_dt')
        
        # Count recurrences: reactive work on asset with prior reactive in last 90 days
        recurrence_count = 0
        
        for asset_id in reactive_completed['asset_id'].dropna().unique():
            asset_reactive = reactive_completed[reactive_completed['asset_id'] == asset_id].copy()
            
            for idx, row in asset_reactive.iterrows():
                if pd.notna(row['completion_dt']):
                    # Check for prior reactive work within 90 days
                    prior_work = asset_reactive[
                        (asset_reactive['completion_dt'] < row['completion_dt']) &
                        (asset_reactive['completion_dt'] >= row['completion_dt'] - pd.Timedelta(days=90))
                    ]
                    
                    if len(prior_work) > 0:
                        recurrence_count += 1
        
        truesignal_value = _safe_division(recurrence_count, len(reactive_completed))
        
        distortion = _calculate_distortion(raw_value, truesignal_value, threshold=0.05)
        
        explanation = (
            f"Raw count shows {raw_value} reactive WOs total. "
            f"TrueSignal identifies {recurrence_count}/{len(reactive_completed)} repeat failures "
            f"({truesignal_value:.2%}), indicating assets with chronic issues requiring root cause analysis."
        )
        
        return {
            'kpi_name': 'Failure Recurrence Index',
            'raw_value': round(raw_value, 2),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Failure Recurrence Index: {str(e)}")


def calculate_maintenance_load_stability(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Maintenance Load Stability (Monthly KPI #4).
    
    Measures consistency of maintenance workload over time.
    Raw: Standard deviation of daily work order count
    TrueSignal: Coefficient of variation accounting for planned vs unplanned work
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        Dictionary with KPI results
    """
    try:
        # Prepare data with dates
        df_copy = df.copy()
        df_copy['creation_dt'] = pd.to_datetime(df_copy['creation_date'], errors='coerce')
        df_copy['date'] = df_copy['creation_dt'].dt.date
        
        # Raw: standard deviation of daily WO counts
        daily_counts = df_copy.groupby('date').size()
        
        if len(daily_counts) > 0:
            raw_value = daily_counts.std()
            mean_daily = daily_counts.mean()
        else:
            raw_value = 0.0
            mean_daily = 0.0
        
        # TrueSignal: coefficient of variation split by work type
        df_copy['is_planned'] = df_copy['type'].str.lower().str.contains('pm|preventive|preventative', na=False)
        
        planned_daily = df_copy[df_copy['is_planned']].groupby('date').size()
        unplanned_daily = df_copy[~df_copy['is_planned']].groupby('date').size()
        
        # Reindex to have all dates
        all_dates = pd.date_range(
            start=df_copy['date'].min(), 
            end=df_copy['date'].max(), 
            freq='D'
        ).date
        
        planned_daily = planned_daily.reindex(all_dates, fill_value=0)
        unplanned_daily = unplanned_daily.reindex(all_dates, fill_value=0)
        
        # Calculate coefficient of variation for unplanned work (higher = less stable)
        unplanned_mean = unplanned_daily.mean()
        unplanned_std = unplanned_daily.std()
        
        truesignal_value = _safe_division(unplanned_std, unplanned_mean) if unplanned_mean > 0 else 0.0
        
        distortion = _calculate_distortion(raw_value, truesignal_value, threshold=0.2)
        
        explanation = (
            f"Raw load stability shows ±{raw_value:.1f} WOs/day variation (mean: {mean_daily:.1f}). "
            f"TrueSignal focuses on unplanned work variability (CV: {truesignal_value:.2f}), "
            f"revealing workflow instability masked by predictable PM scheduling."
        )
        
        return {
            'kpi_name': 'Maintenance Load Stability',
            'raw_value': round(raw_value, 2),
            'truesignal_value': round(truesignal_value, 4),
            'distortion_flag': distortion,
            'explanation': explanation
        }
    except Exception as e:
        raise KPICalculationError(f"Error calculating Maintenance Load Stability: {str(e)}")
    # ============================================================================
# MAIN CALCULATION FUNCTION
# ============================================================================

def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all 13 KPIs and return results as a DataFrame.
    
    Args:
        df: Cleaned work orders DataFrame from load_and_map_data.py
        
    Returns:
        DataFrame with columns: kpi_name, raw_value, truesignal_value, 
        distortion_flag, explanation
        
    Raises:
        KPICalculationError: If any KPI calculation fails
        
    Example:
        >>> from load_and_map_data import load_and_prepare_data
        >>> from calculate_kpis import calculate_all
        >>> df = load_and_prepare_data()
        >>> kpi_results = calculate_all(df)
        >>> print(kpi_results)
    """
    if df.empty:
        raise KPICalculationError("Cannot calculate KPIs on empty DataFrame")
    
    # Define all KPI calculation functions in order
    kpi_functions = [
        # Daily KPIs
        calculate_reactive_work_ratio,
        calculate_pm_compliance,
        calculate_backlog_age,
        calculate_schedule_adherence,
        calculate_emergency_work_percentage,
        
        # Weekly KPIs
        calculate_pm_slippage_rate,
        calculate_reactive_creep_index,
        calculate_mean_time_to_complete,
        calculate_labor_utilization,
        
        # Monthly KPIs
        calculate_pm_effectiveness_score,
        calculate_backlog_growth_rate,
        calculate_failure_recurrence_index,
        calculate_maintenance_load_stability,
    ]
    
    results = []
    errors = []
    
    for kpi_func in kpi_functions:
        try:
            result = kpi_func(df)
            results.append(result)
        except Exception as e:
            error_msg = f"Error in {kpi_func.__name__}: {str(e)}"
            errors.append(error_msg)
            # Add placeholder result
            results.append({
                'kpi_name': kpi_func.__name__.replace('calculate_', '').replace('_', ' ').title(),
                'raw_value': None,
                'truesignal_value': None,
                'distortion_flag': False,
                'explanation': f"Calculation failed: {str(e)}"
            })
    
    # Convert to DataFrame
    kpi_df = pd.DataFrame(results)
    
    # Log any errors
    if errors:
        print("WARNING: Some KPIs failed to calculate:")
        for error in errors:
            print(f"  - {error}")
    
    return kpi_df


if __name__ == "__main__":
    """
    Test KPI calculations with loaded data.
    """
    try:
        # Import data loading module
        from load_and_map_data import load_and_prepare_data
        
        # Load data
        print("Loading data...")
        df = load_and_prepare_data()
        print(f"Loaded {len(df)} work orders")
        
        # Calculate all KPIs
        print("\nCalculating KPIs...")
        kpi_results = calculate_all(df)
        
        # Display results
        print("\n" + "="*80)
        print("KPI CALCULATION RESULTS")
        print("="*80)
        
        for _, row in kpi_results.iterrows():
            print(f"\n{row['kpi_name']}")
            print(f"  Raw Value: {row['raw_value']}")
            print(f"  TrueSignal Value: {row['truesignal_value']}")
            print(f"  Distortion: {'YES' if row['distortion_flag'] else 'NO'}")
            print(f"  {row['explanation']}")
        
        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total KPIs: {len(kpi_results)}")
        print(f"Distortions detected: {kpi_results['distortion_flag'].sum()}")
        
    except ImportError:
        print("ERROR: Could not import load_and_map_data module")
        print("Make sure load_and_map_data.py is in the same directory")
    except Exception as e:
        print(f"ERROR: {str(e)}")