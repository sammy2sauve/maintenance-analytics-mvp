"""
Create database tables for storing asset failure predictions and maintenance suggestions.

This extends the existing database with predictive analytics capabilities.

Usage:
    python create_prediction_tables.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def create_prediction_tables() -> None:
    """Create tables for storing predictions and recommendations."""
    
    db_path = Path("data/db/truesignal.db")
    
    if not db_path.exists():
        print("❌ Database not found at:", db_path)
        print("Run: python create_test_db.py first")
        return
    
    print("Creating prediction tables...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Asset Failure Predictions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_failure_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            prediction_date DATE NOT NULL,
            failure_probability REAL NOT NULL,
            days_to_predicted_failure INTEGER,
            confidence_score REAL,
            mtbf_days REAL,
            days_since_last_pm INTEGER,
            reactive_work_count_90d INTEGER,
            risk_level TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_id, prediction_date)
        )
    """)
    
    # PM Schedule Optimization Suggestions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pm_optimization_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            current_pm_frequency_days INTEGER,
            suggested_pm_frequency_days INTEGER,
            reason TEXT,
            estimated_cost_savings REAL,
            estimated_risk_change REAL,
            confidence_score REAL,
            reactive_work_after_pm_count INTEGER,
            suggestion_date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_id, suggestion_date)
        )
    """)
    
    # Maintenance Insights/Patterns Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            confidence_score REAL,
            impact_level TEXT,
            affected_assets TEXT,
            metric_value REAL,
            insight_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_asset 
        ON asset_failure_predictions(asset_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_date 
        ON asset_failure_predictions(prediction_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_risk 
        ON asset_failure_predictions(risk_level)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_suggestions_asset 
        ON pm_optimization_suggestions(asset_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_insights_type 
        ON maintenance_insights(insight_type)
    """)
    
    conn.commit()
    conn.close()
    
    print("✓ asset_failure_predictions table created")
    print("✓ pm_optimization_suggestions table created")
    print("✓ maintenance_insights table created")
    print("✓ Indexes created")
    print("\n✅ Prediction tables ready!")
    print("Next: Build the prediction algorithms")


if __name__ == "__main__":
    create_prediction_tables()