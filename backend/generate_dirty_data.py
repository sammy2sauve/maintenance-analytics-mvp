"""
Generate realistic dirty data for the TrueSignal maintenance analytics dashboard.

This script populates the work_orders table with data patterns that trigger:
- 7 CRITICAL risk assets (failure probability >= 0.75)
- 15 HIGH risk assets (failure probability >= 0.5)
- 60+ well-maintained assets generating $50K+ cost savings
- ~300 background work orders as normal noise
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

TECHNICIANS = [
    "John Smith", "Bob Johnson", "Maria Garcia", "James Wilson",
    "Sarah Davis", "Mike Brown", "Lisa Anderson", "Tom Martinez"
]

SITES = ["Refinery A", "Refinery B", "Plant C", "Plant D", "Warehouse E"]

TODAY = datetime.now()


def date_str(dt):
    return dt.strftime("%Y-%m-%d")


def generate_critical_assets():
    """7 CRITICAL assets: high reactive frequency, old PM, low MTBF."""
    rows = []
    for i in range(1, 8):
        asset_id = f"PUMP-{i:03d}"
        site = "Refinery A"

        # 8 Reactive COMPLETED work orders spaced ~10 days apart over last 80 days
        for j in range(8):
            days_ago = 80 - (j * 10)  # 80, 70, 60, 50, 40, 30, 20, 10
            creation = TODAY - timedelta(days=days_ago + 1)
            completion = TODAY - timedelta(days=days_ago)
            rows.append({
                "asset_id": asset_id,
                "site": site,
                "type": "Reactive",
                "status": "Completed",
                "technician": random.choice(["John Smith", "Bob Johnson"]),
                "creation_date": date_str(creation),
                "scheduled_start": date_str(creation),
                "start_date": date_str(creation),
                "completion_date": date_str(completion),
                "labor_hours_scheduled": round(random.uniform(2, 6), 1),
                "labor_hours_actual": round(random.uniform(3, 8), 1),
                "downtime_hours": round(random.uniform(4, 12), 1),
                "reactive_followup": 1,
                "priority": "High",
                "due_date": date_str(creation + timedelta(days=1)),
            })

        # 1 old PM COMPLETED, 240 days ago
        old_pm_date = TODAY - timedelta(days=240)
        rows.append({
            "asset_id": asset_id,
            "site": site,
            "type": "PM",
            "status": "Completed",
            "technician": "John Smith",
            "creation_date": date_str(old_pm_date - timedelta(days=3)),
            "scheduled_start": date_str(old_pm_date),
            "start_date": date_str(old_pm_date),
            "completion_date": date_str(old_pm_date),
            "labor_hours_scheduled": 2.0,
            "labor_hours_actual": 2.5,
            "downtime_hours": 1.0,
            "reactive_followup": 0,
            "priority": "Medium",
            "due_date": date_str(old_pm_date),
        })

    return rows


def generate_high_risk_assets():
    """15 HIGH risk assets: moderate reactive frequency, somewhat old PM."""
    rows = []
    for i in range(1, 16):
        asset_id = f"COMP-{i:03d}"
        site = "Refinery B"

        # 4 Reactive COMPLETED work orders spaced ~20 days apart
        for j in range(4):
            days_ago = 70 - (j * 20)  # 70, 50, 30, 10
            creation = TODAY - timedelta(days=days_ago + 1)
            completion = TODAY - timedelta(days=days_ago)
            rows.append({
                "asset_id": asset_id,
                "site": site,
                "type": "Reactive",
                "status": "Completed",
                "technician": random.choice(TECHNICIANS[:4]),
                "creation_date": date_str(creation),
                "scheduled_start": date_str(creation),
                "start_date": date_str(creation),
                "completion_date": date_str(completion),
                "labor_hours_scheduled": round(random.uniform(2, 5), 1),
                "labor_hours_actual": round(random.uniform(2, 6), 1),
                "downtime_hours": round(random.uniform(2, 8), 1),
                "reactive_followup": 1,
                "priority": "Medium",
                "due_date": date_str(creation + timedelta(days=2)),
            })

        # 1 PM COMPLETED, 110 days ago
        pm_date = TODAY - timedelta(days=110)
        rows.append({
            "asset_id": asset_id,
            "site": site,
            "type": "PM",
            "status": "Completed",
            "technician": random.choice(TECHNICIANS),
            "creation_date": date_str(pm_date - timedelta(days=2)),
            "scheduled_start": date_str(pm_date),
            "start_date": date_str(pm_date),
            "completion_date": date_str(pm_date),
            "labor_hours_scheduled": 2.0,
            "labor_hours_actual": 2.0,
            "downtime_hours": 1.0,
            "reactive_followup": 0,
            "priority": "Low",
            "due_date": date_str(pm_date),
        })

    return rows


def generate_cost_savings_assets():
    """60 well-maintained assets: frequent PMs, zero reactive work."""
    rows = []
    for i in range(1, 61):
        asset_id = f"MAINT-{i:03d}"
        site = "Plant C"

        # 3 PM COMPLETED work orders spaced 14 days apart
        # Last PM: 5 days ago, previous: 19 days ago, before that: 33 days ago
        pm_offsets = [5, 19, 33]
        for offset in pm_offsets:
            pm_date = TODAY - timedelta(days=offset)
            rows.append({
                "asset_id": asset_id,
                "site": site,
                "type": "PM",
                "status": "Completed",
                "technician": random.choice(TECHNICIANS[4:]),
                "creation_date": date_str(pm_date - timedelta(days=1)),
                "scheduled_start": date_str(pm_date),
                "start_date": date_str(pm_date),
                "completion_date": date_str(pm_date),
                "labor_hours_scheduled": 1.5,
                "labor_hours_actual": 1.5,
                "downtime_hours": 0.5,
                "reactive_followup": 0,
                "priority": "Low",
                "due_date": date_str(pm_date),
            })

    return rows


def generate_background_assets():
    """~300 background work orders for normal noise."""
    rows = []
    types = ["PM", "Reactive", "Emergency"]
    statuses = ["Completed", "Pending", "In Progress", "Cancelled"]
    priorities = ["Low", "Medium", "High", "Critical"]

    for _ in range(300):
        asset_num = random.randint(100, 999)
        asset_id = f"ASSET-{asset_num}"
        wo_type = random.choice(types)
        status = random.choice(statuses)
        days_ago = random.randint(0, 180)
        creation = TODAY - timedelta(days=days_ago)

        completion = None
        start = None
        if status == "Completed":
            start = creation + timedelta(days=random.randint(0, 2))
            completion = start + timedelta(days=random.randint(0, 3))
        elif status == "In Progress":
            start = creation + timedelta(days=random.randint(0, 2))

        rows.append({
            "asset_id": asset_id,
            "site": random.choice(SITES),
            "type": wo_type,
            "status": status,
            "technician": random.choice(TECHNICIANS),
            "creation_date": date_str(creation),
            "scheduled_start": date_str(creation + timedelta(days=random.randint(0, 3))),
            "start_date": date_str(start) if start else None,
            "completion_date": date_str(completion) if completion else None,
            "labor_hours_scheduled": round(random.uniform(1, 8), 1),
            "labor_hours_actual": round(random.uniform(1, 10), 1) if status == "Completed" else None,
            "downtime_hours": round(random.uniform(0, 6), 1) if wo_type == "Reactive" else round(random.uniform(0, 2), 1),
            "reactive_followup": 1 if wo_type == "Reactive" and random.random() > 0.5 else 0,
            "priority": random.choice(priorities),
            "due_date": date_str(creation + timedelta(days=random.randint(1, 14))),
        })

    return rows


def insert_rows(conn, rows):
    """Insert work order rows into the database."""
    columns = [
        "asset_id", "site", "type", "status", "technician",
        "creation_date", "scheduled_start", "start_date", "completion_date",
        "labor_hours_scheduled", "labor_hours_actual", "downtime_hours",
        "reactive_followup", "priority", "due_date"
    ]
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(columns)
    sql = f"INSERT INTO work_orders ({col_names}) VALUES ({placeholders})"

    for row in rows:
        values = [row.get(col) for col in columns]
        conn.execute(sql, values)

    conn.commit()


def main():
    print(f"Database: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))

    # Clear existing work orders (keep table structure)
    conn.execute("DELETE FROM work_orders")
    # Also clear prediction tables so pipeline can regenerate
    conn.execute("DELETE FROM asset_failure_predictions")
    conn.execute("DELETE FROM pm_optimization_suggestions")
    conn.execute("DELETE FROM maintenance_insights")
    conn.commit()
    print("Cleared existing data.")

    # Generate all work orders
    critical_rows = generate_critical_assets()
    high_rows = generate_high_risk_assets()
    savings_rows = generate_cost_savings_assets()
    background_rows = generate_background_assets()

    all_rows = critical_rows + high_rows + savings_rows + background_rows
    print(f"\nGenerated work orders:")
    print(f"  CRITICAL assets (PUMP-001..007): {len(critical_rows)} WOs")
    print(f"  HIGH risk assets (COMP-001..015): {len(high_rows)} WOs")
    print(f"  Cost savings assets (MAINT-001..060): {len(savings_rows)} WOs")
    print(f"  Background noise: {len(background_rows)} WOs")
    print(f"  TOTAL: {len(all_rows)} work orders")

    insert_rows(conn, all_rows)
    print("\nInserted all work orders into database.")

    # Verify
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM work_orders")
    print(f"\nVerification - Total WOs in DB: {c.fetchone()[0]}")
    c.execute("SELECT type, COUNT(*) FROM work_orders GROUP BY type")
    print(f"By type: {c.fetchall()}")
    c.execute("SELECT COUNT(DISTINCT asset_id) FROM work_orders")
    print(f"Unique assets: {c.fetchone()[0]}")

    conn.close()
    print("\nDone! Now run: python -m backend.pipeline")


if __name__ == "__main__":
    main()
