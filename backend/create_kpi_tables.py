import sqlite3
from pathlib import Path

# Path to the database
db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

# Connect to database
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("Creating KPI tables...")

# --- Create tables ---
c.execute("""
CREATE TABLE IF NOT EXISTS daily_kpis (
    id INTEGER PRIMARY KEY,
    kpi_name TEXT,
    raw_value REAL,
    true_signal_value REAL,
    distortion REAL,
    explanation TEXT,
    period_date DATE
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS weekly_kpis (
    id INTEGER PRIMARY KEY,
    kpi_name TEXT,
    raw_value REAL,
    true_signal_value REAL,
    distortion REAL,
    explanation TEXT,
    period_week TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS monthly_kpis (
    id INTEGER PRIMARY KEY,
    kpi_name TEXT,
    raw_value REAL,
    true_signal_value REAL,
    distortion REAL,
    explanation TEXT,
    period_month TEXT
)
""")

# --- Insert dummy data ---
daily_data = [
    ("Reactive Work Ratio", 0.3, 0.28, 0.02, "Sample daily KPI", "2026-01-25"),
    ("PM Compliance (True)", 0.85, 0.83, 0.02, "Sample daily KPI", "2026-01-25"),
    ("Work Order Backlog Age", 12, 11.5, 0.5, "Sample daily KPI", "2026-01-25")
]

weekly_data = [
    ("PM Slippage Rate", 0.1, 0.09, 0.01, "Sample weekly KPI", "2026-W04"),
    ("Reactive Creep Index", 0.05, 0.045, 0.005, "Sample weekly KPI", "2026-W04")
]

monthly_data = [
    ("PM Effectiveness Score", 0.9, 0.88, 0.02, "Sample monthly KPI", "2026-01"),
    ("Backlog Growth Rate", 0.15, 0.14, 0.01, "Sample monthly KPI", "2026-01")
]

c.executemany("""
INSERT INTO daily_kpis (kpi_name, raw_value, true_signal_value, distortion, explanation, period_date)
VALUES (?, ?, ?, ?, ?, ?)
""", daily_data)

c.executemany("""
INSERT INTO weekly_kpis (kpi_name, raw_value, true_signal_value, distortion, explanation, period_week)
VALUES (?, ?, ?, ?, ?, ?)
""", weekly_data)

c.executemany("""
INSERT INTO monthly_kpis (kpi_name, raw_value, true_signal_value, distortion, explanation, period_month)
VALUES (?, ?, ?, ?, ?, ?)
""", monthly_data)

# Commit and close
conn.commit()
conn.close()

print(f"✅ KPI tables created and populated in {db_path}")
