"""
Predictive maintenance analytics module.

This module provides failure prediction, PM optimization, and pattern detection
using rule-based heuristics and statistical analysis.

Key features:
1. Asset failure probability scoring
2. PM schedule optimization suggestions
3. Maintenance pattern detection
4. Risk level classification
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict


class PredictiveAnalyticsError(Exception):
    """Custom exception for predictive analytics errors."""
    pass


# ============================================================================
# ASSET FAILURE PREDICTION
# ============================================================================

def calculate_mtbf(df: pd.DataFrame, asset_id: str) -> Optional[float]:
    """
    Calculate Mean Time Between Failures (MTBF) for an asset.
    
    MTBF = Average time between reactive maintenance events
    
    Args:
        df: Work orders DataFrame
        asset_id: Asset identifier
        
    Returns:
        MTBF in days, or None if insufficient data
    """
    # Filter reactive work for this asset
    asset_reactive = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('reactive|corrective', na=False)) &
        (df['status'].str.lower().str.contains('complet', na=False))
    ].copy()
    
    if len(asset_reactive) < 2:
        return None
    
    # Sort by completion date
    asset_reactive['completion_dt'] = pd.to_datetime(
        asset_reactive['completion_date'], 
        errors='coerce'
    )
    asset_reactive = asset_reactive.sort_values('completion_dt')
    
    # Calculate time between failures
    time_diffs = asset_reactive['completion_dt'].diff().dt.days
    
    # Remove NaN (first row) and outliers (>365 days)
    time_diffs = time_diffs.dropna()
    time_diffs = time_diffs[time_diffs <= 365]
    
    if len(time_diffs) == 0:
        return None
    
    return float(time_diffs.mean())


def calculate_days_since_last_pm(df: pd.DataFrame, asset_id: str) -> Optional[int]:
    """
    Calculate days since last completed PM for an asset.
    
    Args:
        df: Work orders DataFrame
        asset_id: Asset identifier
        
    Returns:
        Days since last PM, or None if no PM history
    """
    # Filter completed PM work for this asset
    asset_pm = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
        (df['status'].str.lower().str.contains('complet', na=False))
    ].copy()
    
    if len(asset_pm) == 0:
        return None
    
    # Get most recent PM completion date
    asset_pm['completion_dt'] = pd.to_datetime(
        asset_pm['completion_date'], 
        errors='coerce'
    )
    
    last_pm_date = asset_pm['completion_dt'].max()
    
    if pd.isna(last_pm_date):
        return None
    
    days_since = (pd.Timestamp.now() - last_pm_date).days
    return int(days_since)


def count_recent_reactive_work(
    df: pd.DataFrame, 
    asset_id: str, 
    days: int = 90
) -> int:
    """
    Count reactive work orders for an asset in recent period.
    
    Args:
        df: Work orders DataFrame
        asset_id: Asset identifier
        days: Number of days to look back (default 90)
        
    Returns:
        Count of reactive work orders
    """
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
    
    recent_reactive = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('reactive|corrective', na=False)) &
        (pd.to_datetime(df['creation_date'], errors='coerce') >= cutoff_date)
    ]
    
    return len(recent_reactive)


def calculate_failure_probability(
    mtbf: Optional[float],
    days_since_pm: Optional[int],
    reactive_count_90d: int,
    asset_has_pm_history: bool,
    days_since_last_work: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Calculate failure probability score for an asset.
    
    Scoring methodology:
    - MTBF-based: If days since PM > MTBF, probability increases
    - Frequency-based: More reactive work = higher probability
    - Maintenance gap: No recent PM = higher risk
    
    Args:
        mtbf: Mean time between failures in days
        days_since_pm: Days since last PM
        reactive_count_90d: Reactive work count in last 90 days
        asset_has_pm_history: Whether asset has PM maintenance history
        
    Returns:
        Tuple of (failure_probability, confidence_score)
        - failure_probability: 0.0 to 1.0
        - confidence_score: 0.0 to 1.0 (how confident we are in prediction)
    """
    probability = 0.0
    confidence = 0.5  # Base confidence
    
    # Factor 1: MTBF-based probability
    if mtbf is not None and days_since_pm is not None:
        # Probability increases as we approach/exceed MTBF
        mtbf_ratio = days_since_pm / mtbf
        mtbf_probability = min(mtbf_ratio, 1.0)  # Cap at 100%
        probability += mtbf_probability * 0.5  # 50% weight
        confidence += 0.3  # Higher confidence with MTBF data
    
    # Factor 2: Recent reactive work frequency
    if reactive_count_90d > 0:
        # More reactive work = higher probability
        # Scale: 0-2 events = low, 3-5 = medium, 6+ = high
        frequency_probability = min(reactive_count_90d / 6.0, 1.0)
        probability += frequency_probability * 0.3  # 30% weight
        confidence += 0.2
    
    # Factor 3: PM maintenance gap
    if asset_has_pm_history:
        if days_since_pm is not None and days_since_pm > 90:
            # No PM in 90+ days increases risk
            gap_probability = min((days_since_pm - 90) / 180, 0.5)
            probability += gap_probability * 0.2  # 20% weight
        confidence += 0.1
    else:
        # No PM history is a red flag
        probability += 0.2
        confidence -= 0.1
    
    # Factor 4: Recent maintenance credit — any completed WO in last 30 days reduces risk
    if days_since_last_work is not None:
        if days_since_last_work <= 30:
            probability -= 0.25
        elif days_since_last_work <= 60:
            probability -= 0.12

    # Normalize
    probability = max(min(probability, 1.0), 0.0)
    confidence = max(min(confidence, 1.0), 0.1)

    return probability, confidence


def calculate_days_since_last_work(df: pd.DataFrame, asset_id: str) -> Optional[int]:
    """Days since any completed work order (PM or corrective) for an asset."""
    asset_work = df[
        (df['asset_id'] == asset_id) &
        (df['status'].str.lower().str.contains('complet', na=False))
    ].copy()
    if len(asset_work) == 0:
        return None
    asset_work['completion_dt'] = pd.to_datetime(asset_work['completion_date'], errors='coerce')
    last_date = asset_work['completion_dt'].max()
    if pd.isna(last_date):
        return None
    return int((pd.Timestamp.now() - last_date).days)


def classify_risk_level(probability: float) -> str:
    """
    Classify failure probability into risk levels.
    
    Args:
        probability: Failure probability (0.0 to 1.0)
        
    Returns:
        Risk level: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
    """
    if probability >= 0.75:
        return 'CRITICAL'
    elif probability >= 0.5:
        return 'HIGH'
    elif probability >= 0.25:
        return 'MEDIUM'
    else:
        return 'LOW'


def generate_failure_recommendation(
    probability: float,
    risk_level: str,
    days_since_pm: Optional[int],
    mtbf: Optional[float],
    days_to_failure: Optional[int]
) -> str:
    """
    Generate actionable recommendation based on failure prediction.
    
    Args:
        probability: Failure probability
        risk_level: Risk classification
        days_since_pm: Days since last PM
        mtbf: Mean time between failures
        days_to_failure: Estimated days until failure
        
    Returns:
        Human-readable recommendation string
    """
    if risk_level == 'CRITICAL':
        if days_to_failure and days_to_failure <= 7:
            return f"URGENT: Schedule immediate PM. Predicted failure within {days_to_failure} days."
        else:
            return "High failure risk detected. Schedule PM within next 7 days to prevent breakdown."
    
    elif risk_level == 'HIGH':
        if days_since_pm and days_since_pm > 60:
            return f"Overdue for PM ({days_since_pm} days since last service). Schedule within 2 weeks."
        else:
            return "Elevated failure risk. Schedule PM within next 2-3 weeks."
    
    elif risk_level == 'MEDIUM':
        return "Moderate risk. Monitor closely and schedule PM within next 30 days."
    
    else:  # LOW
        if mtbf:
            return f"Low risk. Next PM recommended in {int(mtbf * 0.8)} days based on MTBF."
        else:
            return "Low risk. Continue routine maintenance schedule."
def predict_asset_failures(
    df: pd.DataFrame,
    lookback_days: int = 90,
    min_reactive_events: int = 1
) -> pd.DataFrame:
    """
    Predict failure probability for all assets in the system.
    
    This is the main prediction function that analyzes each asset and
    generates failure predictions with risk levels and recommendations.
    
    Args:
        df: Work orders DataFrame
        lookback_days: Days to look back for reactive work analysis
        min_reactive_events: Minimum reactive events needed for MTBF calculation
        
    Returns:
        DataFrame with predictions for each asset containing:
        - asset_id
        - failure_probability
        - confidence_score
        - days_to_predicted_failure
        - mtbf_days
        - days_since_last_pm
        - reactive_work_count_90d
        - risk_level
        - recommendation
        
    Raises:
        PredictiveAnalyticsError: If prediction fails
    """
    try:
        # Get unique assets
        assets = df['asset_id'].dropna().unique()
        
        predictions = []
        current_date = datetime.now()
        
        for asset_id in assets:
            # Calculate metrics for this asset
            mtbf = calculate_mtbf(df, asset_id)
            days_since_pm = calculate_days_since_last_pm(df, asset_id)
            reactive_count = count_recent_reactive_work(df, asset_id, lookback_days)
            days_since_work = calculate_days_since_last_work(df, asset_id)

            # Check if asset has PM history
            asset_pm_count = len(df[
                (df['asset_id'] == asset_id) &
                (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False))
            ])
            has_pm_history = asset_pm_count > 0

            # Calculate failure probability
            probability, confidence = calculate_failure_probability(
                mtbf=mtbf,
                days_since_pm=days_since_pm,
                reactive_count_90d=reactive_count,
                asset_has_pm_history=has_pm_history,
                days_since_last_work=days_since_work,
            )
            
            # Estimate days to failure
            days_to_failure = None
            if mtbf is not None and days_since_pm is not None:
                # Predicted failure when days_since_pm reaches MTBF
                days_to_failure = max(int(mtbf - days_since_pm), 0)
            
            # Classify risk
            risk_level = classify_risk_level(probability)
            
            # Generate recommendation
            recommendation = generate_failure_recommendation(
                probability=probability,
                risk_level=risk_level,
                days_since_pm=days_since_pm,
                mtbf=mtbf,
                days_to_failure=days_to_failure
            )
            
            predictions.append({
                'asset_id': asset_id,
                'prediction_date': current_date.strftime('%Y-%m-%d'),
                'failure_probability': round(probability, 4),
                'confidence_score': round(confidence, 4),
                'days_to_predicted_failure': days_to_failure,
                'mtbf_days': round(mtbf, 2) if mtbf else None,
                'days_since_last_pm': days_since_pm,
                'reactive_work_count_90d': reactive_count,
                'risk_level': risk_level,
                'recommendation': recommendation
            })
        
        # Convert to DataFrame and sort by risk
        predictions_df = pd.DataFrame(predictions)
        
        # Sort by probability (highest risk first)
        predictions_df = predictions_df.sort_values(
            'failure_probability', 
            ascending=False
        )
        
        return predictions_df
        
    except Exception as e:
        raise PredictiveAnalyticsError(f"Failed to predict asset failures: {str(e)}")


# ============================================================================
# PM SCHEDULE OPTIMIZATION
# ============================================================================

def analyze_pm_effectiveness_per_asset(df: pd.DataFrame, asset_id: str) -> Dict[str, Any]:
    """
    Analyze how effective PM is for preventing reactive work on an asset.
    
    Methodology:
    - Look at reactive work within 30 days after each PM
    - If reactive work follows PM frequently, PM may be ineffective or too infrequent
    - If no reactive work follows PM, PM may be more frequent than needed
    
    Args:
        df: Work orders DataFrame
        asset_id: Asset identifier
        
    Returns:
        Dictionary with effectiveness metrics
    """
    # Get completed PMs for this asset
    asset_pm = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
        (df['status'].str.lower().str.contains('complet', na=False))
    ].copy()
    
    if len(asset_pm) == 0:
        return {
            'has_pm_history': False,
            'pm_count': 0,
            'reactive_after_pm_count': 0,
            'effectiveness_score': 0.0
        }
    
    asset_pm['completion_dt'] = pd.to_datetime(asset_pm['completion_date'], errors='coerce')
    
    # Get reactive work for this asset
    asset_reactive = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('reactive|corrective', na=False))
    ].copy()
    
    asset_reactive['creation_dt'] = pd.to_datetime(asset_reactive['creation_date'], errors='coerce')
    
    # Count reactive work within 30 days after each PM
    reactive_after_pm = 0
    
    for _, pm_row in asset_pm.iterrows():
        pm_date = pm_row['completion_dt']
        if pd.isna(pm_date):
            continue
        
        # Count reactive work 1-30 days after this PM
        reactive_in_window = asset_reactive[
            (asset_reactive['creation_dt'] > pm_date) &
            (asset_reactive['creation_dt'] <= pm_date + pd.Timedelta(days=30))
        ]
        
        reactive_after_pm += len(reactive_in_window)
    
    # Calculate effectiveness score
    # Low reactive work after PM = high effectiveness
    effectiveness_score = max(0.0, 1.0 - (reactive_after_pm / max(len(asset_pm), 1)))
    
    return {
        'has_pm_history': True,
        'pm_count': len(asset_pm),
        'reactive_after_pm_count': reactive_after_pm,
        'effectiveness_score': effectiveness_score
    }


def calculate_current_pm_frequency(df: pd.DataFrame, asset_id: str) -> Optional[int]:
    """
    Calculate current average PM frequency for an asset.
    
    Args:
        df: Work orders DataFrame
        asset_id: Asset identifier
        
    Returns:
        Average days between PMs, or None if insufficient history
    """
    asset_pm = df[
        (df['asset_id'] == asset_id) &
        (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
        (df['status'].str.lower().str.contains('complet', na=False))
    ].copy()
    
    if len(asset_pm) < 2:
        return None
    
    asset_pm['completion_dt'] = pd.to_datetime(asset_pm['completion_date'], errors='coerce')
    asset_pm = asset_pm.sort_values('completion_dt')
    
    time_diffs = asset_pm['completion_dt'].diff().dt.days
    time_diffs = time_diffs.dropna()
    
    if len(time_diffs) == 0:
        return None
    
    return int(time_diffs.mean())


def suggest_pm_frequency_optimization(
    current_frequency: Optional[int],
    effectiveness_score: float,
    reactive_after_pm_count: int,
    mtbf: Optional[float]
) -> Tuple[Optional[int], str, float]:
    """
    Suggest optimized PM frequency based on effectiveness analysis.
    
    Logic:
    - High effectiveness + no reactive work = Can reduce frequency (save cost)
    - Low effectiveness + reactive work after PM = Increase frequency (reduce failures)
    - Moderate effectiveness = Keep current schedule
    
    Args:
        current_frequency: Current PM frequency in days
        effectiveness_score: PM effectiveness score (0-1)
        reactive_after_pm_count: Count of reactive work after PMs
        mtbf: Mean time between failures
        
    Returns:
        Tuple of (suggested_frequency, reason, confidence)
    """
    if current_frequency is None:
        return None, "Insufficient PM history to optimize", 0.0
    
    suggested_frequency = current_frequency
    reason = "Maintain current schedule"
    confidence = 0.5
    
    # High effectiveness - can potentially reduce frequency
    if effectiveness_score >= 0.8 and reactive_after_pm_count == 0:
        # Increase frequency by 25% (less frequent)
        suggested_frequency = int(current_frequency * 1.25)
        reason = "High PM effectiveness with no failures. Safe to reduce frequency by 25%."
        confidence = 0.7
    
    # Low effectiveness - should increase frequency
    elif effectiveness_score < 0.5 and reactive_after_pm_count >= 3:
        # Decrease frequency by 25% (more frequent)
        suggested_frequency = int(current_frequency * 0.75)
        reason = f"Low PM effectiveness with {reactive_after_pm_count} failures after PM. Increase frequency by 25%."
        confidence = 0.8
    
    # Moderate effectiveness with some issues
    elif effectiveness_score < 0.7 and reactive_after_pm_count >= 1:
        # Slight decrease in frequency
        suggested_frequency = int(current_frequency * 0.9)
        reason = f"Moderate effectiveness with {reactive_after_pm_count} failures. Slightly increase frequency."
        confidence = 0.6
    
    # MTBF-based validation
    if mtbf is not None and suggested_frequency is not None:
        # PM should happen before MTBF
        if suggested_frequency > mtbf * 0.8:
            suggested_frequency = int(mtbf * 0.75)
            reason += f" Adjusted to align with MTBF ({mtbf:.0f} days)."
            confidence = 0.9
    
    return suggested_frequency, reason, confidence
def optimize_pm_schedules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate PM schedule optimization suggestions for all assets.
    
    Analyzes PM effectiveness and suggests frequency adjustments to:
    - Reduce unnecessary PM (cost savings)
    - Increase PM where needed (reduce failures)
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        DataFrame with optimization suggestions containing:
        - asset_id
        - current_pm_frequency_days
        - suggested_pm_frequency_days
        - reason
        - estimated_cost_savings
        - estimated_risk_change
        - confidence_score
        - reactive_work_after_pm_count
        
    Raises:
        PredictiveAnalyticsError: If optimization fails
    """
    try:
        assets = df['asset_id'].dropna().unique()
        suggestions = []
        current_date = datetime.now()
        
        # Assume average labor cost per PM (can be parameterized later)
        avg_pm_cost = 200  # dollars
        
        for asset_id in assets:
            # Analyze PM effectiveness
            effectiveness = analyze_pm_effectiveness_per_asset(df, asset_id)
            
            if not effectiveness['has_pm_history']:
                continue  # Skip assets with no PM history
            
            # Get current PM frequency
            current_freq = calculate_current_pm_frequency(df, asset_id)
            
            if current_freq is None:
                continue  # Need at least 2 PMs to calculate frequency
            
            # Get MTBF for validation
            mtbf = calculate_mtbf(df, asset_id)
            
            # Suggest optimization
            suggested_freq, reason, confidence = suggest_pm_frequency_optimization(
                current_frequency=current_freq,
                effectiveness_score=effectiveness['effectiveness_score'],
                reactive_after_pm_count=effectiveness['reactive_after_pm_count'],
                mtbf=mtbf
            )
            
            if suggested_freq is None or suggested_freq == current_freq:
                continue  # No change suggested
            
            # Calculate cost impact
            # Fewer PMs = cost savings, More PMs = cost increase
            pms_per_year_current = 365 / current_freq
            pms_per_year_suggested = 365 / suggested_freq
            pm_diff = pms_per_year_current - pms_per_year_suggested
            estimated_savings = max(pm_diff * avg_pm_cost, 0)
            
            # Estimate risk change
            # Reducing frequency = slight risk increase
            # Increasing frequency = risk decrease
            if suggested_freq > current_freq:
                risk_change = 0.05  # +5% risk
            else:
                risk_change = -0.10  # -10% risk
            
            suggestions.append({
                'asset_id': asset_id,
                'current_pm_frequency_days': current_freq,
                'suggested_pm_frequency_days': suggested_freq,
                'reason': reason,
                'estimated_cost_savings': round(estimated_savings, 2),
                'estimated_risk_change': round(risk_change, 4),
                'confidence_score': round(confidence, 4),
                'reactive_work_after_pm_count': effectiveness['reactive_after_pm_count'],
                'suggestion_date': current_date.strftime('%Y-%m-%d')
            })
        
        # Convert to DataFrame and sort by savings potential
        suggestions_df = pd.DataFrame(suggestions)
        
        if not suggestions_df.empty:
            suggestions_df = suggestions_df.sort_values(
                'estimated_cost_savings',
                ascending=False
            )
        
        return suggestions_df
        
    except Exception as e:
        raise PredictiveAnalyticsError(f"Failed to optimize PM schedules: {str(e)}")


# ============================================================================
# PATTERN DETECTION & INSIGHTS
# ============================================================================

def detect_day_of_week_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect patterns in reactive work by day of week.
    
    Example insights:
    - "60% of reactive work happens on Mondays"
    - "Fridays have 2x higher reactive work rate"
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    # Filter reactive work
    reactive_df = df[
        df['type'].str.lower().str.contains('reactive|corrective', na=False)
    ].copy()
    
    if len(reactive_df) == 0:
        return insights
    
    # Parse creation dates and extract day of week
    reactive_df['creation_dt'] = pd.to_datetime(reactive_df['creation_date'], errors='coerce')
    reactive_df['day_of_week'] = reactive_df['creation_dt'].dt.day_name()
    
    # Count by day of week
    day_counts = reactive_df['day_of_week'].value_counts()
    total_reactive = len(reactive_df)
    
    # Find highest day
    if len(day_counts) > 0:
        top_day = day_counts.index[0]
        top_count = day_counts.iloc[0]
        top_percentage = (top_count / total_reactive) * 100
        
        # Only report if significantly higher than average
        avg_percentage = 100 / 7  # ~14.3%
        
        if top_percentage > avg_percentage * 1.5:  # 50% higher than average
            insights.append({
                'insight_type': 'day_of_week_pattern',
                'title': f'{top_percentage:.0f}% of reactive work occurs on {top_day}s',
                'description': f'{top_count} out of {total_reactive} reactive work orders were created on {top_day}. '
                              f'Consider investigating root causes specific to this day.',
                'confidence_score': 0.8,
                'impact_level': 'MEDIUM',
                'metric_value': top_percentage
            })
    
    return insights


def detect_technician_performance_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect patterns in technician performance.
    
    Example insights:
    - "Technician A has 50% lower rework rate than average"
    - "Technician B completes work 30% faster"
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    # Filter completed work
    completed_df = df[
        df['status'].str.lower().str.contains('complet', na=False)
    ].copy()
    
    if len(completed_df) < 20:  # Need sufficient data
        return insights
    
    # Calculate rework rate per technician (reactive followup flag)
    tech_stats = completed_df.groupby('technician').agg({
        'reactive_followup': 'sum',
        'work_order_id': 'count'
    }).reset_index()
    
    tech_stats.columns = ['technician', 'rework_count', 'total_jobs']
    tech_stats['rework_rate'] = tech_stats['rework_count'] / tech_stats['total_jobs']
    
    # Filter technicians with at least 10 jobs
    tech_stats = tech_stats[tech_stats['total_jobs'] >= 10]
    
    if len(tech_stats) < 2:
        return insights
    
    # Calculate average rework rate
    avg_rework_rate = tech_stats['rework_rate'].mean()
    
    # Find best and worst performers
    best_tech = tech_stats.loc[tech_stats['rework_rate'].idxmin()]
    worst_tech = tech_stats.loc[tech_stats['rework_rate'].idxmax()]
    
    # Report significant differences
    if best_tech['rework_rate'] < avg_rework_rate * 0.5:  # 50% better than average
        improvement_pct = ((avg_rework_rate - best_tech['rework_rate']) / avg_rework_rate) * 100
        
        insights.append({
            'insight_type': 'technician_performance',
            'title': f"{best_tech['technician']} has {improvement_pct:.0f}% lower rework rate",
            'description': f"Rework rate of {best_tech['rework_rate']:.1%} vs team average of {avg_rework_rate:.1%}. "
                          f"Consider sharing best practices from this technician.",
            'confidence_score': 0.7,
            'impact_level': 'HIGH',
            'metric_value': improvement_pct
        })
    
    if worst_tech['rework_rate'] > avg_rework_rate * 1.5:  # 50% worse than average
        increase_pct = ((worst_tech['rework_rate'] - avg_rework_rate) / avg_rework_rate) * 100
        
        insights.append({
            'insight_type': 'technician_performance',
            'title': f"{worst_tech['technician']} has {increase_pct:.0f}% higher rework rate",
            'description': f"Rework rate of {worst_tech['rework_rate']:.1%} vs team average of {avg_rework_rate:.1%}. "
                          f"Consider additional training or support.",
            'confidence_score': 0.7,
            'impact_level': 'MEDIUM',
            'metric_value': increase_pct
        })
    
    return insights


def detect_asset_reliability_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect patterns in asset reliability.
    
    Example insights:
    - "Asset #123 fails every 45 days consistently"
    - "3 assets account for 60% of all reactive work"
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    # Find assets with highest reactive work
    reactive_df = df[
        df['type'].str.lower().str.contains('reactive|corrective', na=False)
    ]
    
    asset_reactive_counts = reactive_df['asset_id'].value_counts()
    total_reactive = len(reactive_df)
    
    if total_reactive < 10:
        return insights
    
    # Find top 3 problematic assets
    top_3_assets = asset_reactive_counts.head(3)
    top_3_total = top_3_assets.sum()
    top_3_percentage = (top_3_total / total_reactive) * 100
    
    if top_3_percentage > 40:  # Top 3 assets account for >40% of reactive work
        asset_list = ', '.join(top_3_assets.index.tolist())
        
        insights.append({
            'insight_type': 'asset_reliability',
            'title': f'Top 3 assets account for {top_3_percentage:.0f}% of all reactive work',
            'description': f'Assets {asset_list} have generated {top_3_total} out of {total_reactive} '
                          f'reactive work orders. Focus reliability improvements on these assets.',
            'confidence_score': 0.9,
            'impact_level': 'HIGH',
            'affected_assets': asset_list,
            'metric_value': top_3_percentage
        })
    
    return insights
def detect_high_failure_assets(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect assets with high failure rates."""
    insights = []
    assets = df['asset_id'].dropna().unique()
    
    for asset_id in assets:
        reactive_90d = count_recent_reactive_work(df, asset_id, days=90)
        
        if reactive_90d >= 5:  # 5+ failures in 3 months
            mtbf = calculate_mtbf(df, asset_id)
            
            insights.append({
                'insight_type': 'high_failure_rate',
                'title': f'Asset {asset_id} has {reactive_90d} failures in past 90 days',
                'description': f'This asset is experiencing frequent failures. '
                              f'{"MTBF: " + str(int(mtbf)) + " days. " if mtbf else ""}'
                              f'Recommend root cause analysis and potential replacement evaluation.',
                'confidence_score': 0.95,
                'impact_level': 'HIGH',
                'affected_assets': asset_id,
                'metric_value': float(reactive_90d)
            })
    
    return sorted(insights, key=lambda x: x['metric_value'], reverse=True)[:3]


def detect_cost_saving_opportunities(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect potential cost savings from optimizing maintenance."""
    insights = []
    reactive_df = df[df['type'].str.lower().str.contains('reactive|corrective', na=False)].copy()
    
    if len(reactive_df) == 0:
        return insights
    
    avg_reactive_cost = 600
    avg_pm_cost = 200
    asset_reactive_counts = reactive_df['asset_id'].value_counts()
    high_cost_assets = []
    
    for asset_id, reactive_count in asset_reactive_counts.items():
        if reactive_count >= 4:
            reactive_cost = reactive_count * avg_reactive_cost
            estimated_pm_cost = 4 * avg_pm_cost
            potential_savings = reactive_cost - estimated_pm_cost
            
            if potential_savings > 1000:
                high_cost_assets.append({
                    'asset_id': asset_id,
                    'reactive_count': reactive_count,
                    'savings': potential_savings
                })
    
    if len(high_cost_assets) >= 3:
        total_savings = sum(a['savings'] for a in high_cost_assets[:3])
        asset_list = ', '.join([a['asset_id'] for a in high_cost_assets[:3]])
        
        insights.append({
            'insight_type': 'cost_optimization',
            'title': f'Implementing PM schedules could save ${total_savings:,.0f} annually',
            'description': f'Assets {asset_list} have high reactive maintenance costs. '
                          f'Implementing preventive maintenance schedules could reduce costs by '
                          f'${total_savings:,.0f} per year.',
            'confidence_score': 0.85,
            'impact_level': 'HIGH',
            'affected_assets': asset_list,
            'metric_value': float(total_savings)
        })
    
    return insights


def detect_pm_coverage_gaps(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect assets without proper PM coverage."""
    insights = []
    all_assets = df['asset_id'].dropna().unique()
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=180)
    
    recent_pm = df[
        (df['type'].str.lower().str.contains('pm|preventive|preventative', na=False)) &
        (pd.to_datetime(df['completion_date'], errors='coerce') >= cutoff_date)
    ]
    
    assets_with_pm = set(recent_pm['asset_id'].unique())
    assets_without_pm = set(all_assets) - assets_with_pm
    
    if len(assets_without_pm) >= 5:
        coverage_rate = (len(assets_with_pm) / len(all_assets)) * 100
        
        insights.append({
            'insight_type': 'pm_coverage_gap',
            'title': f'{len(assets_without_pm)} assets have no PM in past 6 months',
            'description': f'Only {coverage_rate:.0f}% of assets have received preventive maintenance '
                          f'in the past 180 days. {len(assets_without_pm)} assets are at risk of '
                          f'unexpected failures due to lack of PM coverage.',
            'confidence_score': 0.90,
            'impact_level': 'MEDIUM',
            'affected_assets': ', '.join(list(assets_without_pm)[:5]),
            'metric_value': float(len(assets_without_pm))
        })
    
    return insights


def detect_workload_imbalances(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect workload distribution issues."""
    insights = []
    tech_counts = df['technician'].value_counts()
    
    if len(tech_counts) >= 3:
        total_work = len(df)
        top_2_work = tech_counts.head(2).sum()
        top_2_percentage = (top_2_work / total_work) * 100
        
        if top_2_percentage > 60:
            insights.append({
                'insight_type': 'workload_imbalance',
                'title': f'2 technicians handling {top_2_percentage:.0f}% of all work orders',
                'description': f'Workload is heavily concentrated on {tech_counts.index[0]} and '
                              f'{tech_counts.index[1]}. Consider redistributing work to prevent '
                              f'burnout and improve response times.',
                'confidence_score': 0.80,
                'impact_level': 'MEDIUM',
                'metric_value': float(top_2_percentage)
            })
    
    return insights


def detect_recurring_issues(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect recurring issues that suggest systemic problems."""
    insights = []
    reactive_df = df[df['type'].str.lower().str.contains('reactive|corrective', na=False)].copy()
    
    if len(reactive_df) < 10:
        return insights
    
    asset_counts = reactive_df['asset_id'].value_counts()
    recurring_assets = asset_counts[asset_counts >= 4]
    
    if len(recurring_assets) > 0:
        worst_asset = recurring_assets.index[0]
        event_count = recurring_assets.iloc[0]
        
        insights.append({
            'insight_type': 'recurring_failure',
            'title': f'Asset {worst_asset} has {event_count} repeated failures',
            'description': f'This asset is experiencing recurring issues. Review failure patterns '
                          f'and consider comprehensive inspection or replacement to address root cause.',
            'confidence_score': 0.85,
            'impact_level': 'HIGH',
            'affected_assets': worst_asset,
            'metric_value': float(event_count)
        })
    
    return insights


def generate_maintenance_insights(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate actionable maintenance insights from pattern detection.
    
    Combines multiple pattern detection algorithms to provide
    strategic insights for maintenance optimization.
    
    Args:
        df: Work orders DataFrame
        
    Returns:
        DataFrame with insights containing:
        - insight_type
        - title
        - description
        - confidence_score
        - impact_level
        - affected_assets (if applicable)
        - metric_value
        
    Raises:
        PredictiveAnalyticsError: If insight generation fails
    """
    try:
        all_insights = []
        current_date = datetime.now()
        
        # Run all pattern detection algorithms
        all_insights.extend(detect_day_of_week_patterns(df))
        all_insights.extend(detect_technician_performance_patterns(df))
        all_insights.extend(detect_asset_reliability_patterns(df))

        # NEW INSIGHT TYPES
        all_insights.extend(detect_high_failure_assets(df))
        all_insights.extend(detect_cost_saving_opportunities(df))
        all_insights.extend(detect_pm_coverage_gaps(df))
        all_insights.extend(detect_workload_imbalances(df))
        all_insights.extend(detect_recurring_issues(df))
        
        # Add timestamp to all insights
        for insight in all_insights:
            insight['insight_date'] = current_date.strftime('%Y-%m-%d')
        
        # Convert to DataFrame
        insights_df = pd.DataFrame(all_insights)
        
        # Sort by impact level and confidence
        impact_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        
        if not insights_df.empty:
            insights_df['impact_rank'] = insights_df['impact_level'].map(impact_order)
            insights_df = insights_df.sort_values(
                ['impact_rank', 'confidence_score'],
                ascending=[False, False]
            )
            insights_df = insights_df.drop('impact_rank', axis=1)
        
        return insights_df
        
    except Exception as e:
        raise PredictiveAnalyticsError(f"Failed to generate insights: {str(e)}")


if __name__ == "__main__":
    """
    Test predictive analytics functions.
    """
    try:
        from load_and_map_data import load_and_prepare_data
        
        print("Loading data...")
        df = load_and_prepare_data()
        print(f"✓ Loaded {len(df)} work orders\n")
        
        print("="*70)
        print("TESTING FAILURE PREDICTIONS")
        print("="*70)
        predictions = predict_asset_failures(df)
        print(f"\n✓ Generated {len(predictions)} asset predictions")
        print("\nTop 5 High-Risk Assets:")
        print(predictions.head()[['asset_id', 'failure_probability', 'risk_level', 'recommendation']])
        
        print("\n" + "="*70)
        print("TESTING PM OPTIMIZATION")
        print("="*70)
        optimizations = optimize_pm_schedules(df)
        print(f"\n✓ Generated {len(optimizations)} optimization suggestions")
        if not optimizations.empty:
            print("\nTop 3 Cost Saving Opportunities:")
            print(optimizations.head(3)[['asset_id', 'current_pm_frequency_days', 
                                         'suggested_pm_frequency_days', 'estimated_cost_savings']])
        
        print("\n" + "="*70)
        print("TESTING PATTERN DETECTION")
        print("="*70)
        insights = generate_maintenance_insights(df)
        print(f"\n✓ Generated {len(insights)} insights")
        if not insights.empty:
            print("\nKey Insights:")
            for _, insight in insights.iterrows():
                print(f"\n• {insight['title']}")
                print(f"  {insight['description']}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")