"""
Fix KPI table schema by dropping and recreating tables.
Save as: fix_kpi_schema.py
"""

import sqlite3
from pathlib import Path

def fix_kpi_tables():
    """Drop and recreate KPI tables with correct schema."""
    
    db_path = Path("data/db/truesignal.db")
    
    if not db_path.exists():
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Dropping old KPI tables...")
    cursor.execute("DROP TABLE IF EXISTS daily_kpis")
    cursor.execute("DROP TABLE IF EXISTS weekly_kpis")
    cursor.execute("DROP TABLE IF EXISTS monthly_kpis")
    
    print("✓ Old tables dropped")
    
    print("\nCreating new KPI tables with correct schema...")
    
    # Daily KPIs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_date DATE NOT NULL,
            kpi_name TEXT NOT NULL,
            raw_value REAL,
            truesignal_value REAL,
            distortion_flag BOOLEAN NOT NULL DEFAULT 0,
            explanation_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_date, kpi_name)
        )
    """)
    
    # Weekly KPIs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_week TEXT NOT NULL,
            kpi_name TEXT NOT NULL,
            raw_value REAL,
            truesignal_value REAL,
            distortion_flag BOOLEAN NOT NULL DEFAULT 0,
            explanation_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_week, kpi_name)
        )
    """)
    
    # Monthly KPIs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_month TEXT NOT NULL,
            kpi_name TEXT NOT NULL,
            raw_value REAL,
            truesignal_value REAL,
            distortion_flag BOOLEAN NOT NULL DEFAULT 0,
            explanation_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_month, kpi_name)
        )
    """)
    
    conn.commit()
    conn.close()
    
    print("✓ New tables created with correct schema")
    print("\n✅ Done! Now run: python backend/pipeline.py")

if __name__ == "__main__":
    fix_kpi_tables()