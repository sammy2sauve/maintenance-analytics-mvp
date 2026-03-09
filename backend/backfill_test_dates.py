"""
Backfill test prediction data across multiple dates so date range filters
can be verified before production data accumulates.

Creates copies of existing predictions at:
  - 8 days ago  (shows in Last 30 Days, Last 90 Days, All Time — NOT Last 7 Days)
  - 35 days ago (shows in Last 90 Days, All Time — NOT Last 7 or 30 Days)
  - 95 days ago (shows in All Time only)

Each backfilled batch has slightly degraded risk scores to make the
differences visible in the charts.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

def degrade_risk(risk_level, steps=1):
    """Shift risk level toward CRITICAL by `steps`."""
    idx = RISK_LEVELS.index(risk_level)
    return RISK_LEVELS[min(idx + steps, len(RISK_LEVELS) - 1)]

def backfill(conn, days_ago, prob_multiplier, risk_degradation_steps, label):
    cur = conn.cursor()
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

    # Skip if already backfilled for this date
    cur.execute(
        "SELECT COUNT(*) FROM asset_failure_predictions WHERE prediction_date = ?",
        (target_date,)
    )
    if cur.fetchone()[0] > 0:
        print(f"  {label} ({target_date}): already exists, skipping")
        return

    # Fetch the base (most recent) predictions
    cur.execute("""
        SELECT asset_id, failure_probability, days_to_predicted_failure,
               confidence_score, mtbf_days, days_since_last_pm,
               reactive_work_count_90d, risk_level, recommendation
        FROM asset_failure_predictions
        WHERE prediction_date = (SELECT MAX(prediction_date) FROM asset_failure_predictions)
    """)
    rows = cur.fetchall()

    backfilled = []
    for row in rows:
        (asset_id, prob, days_to_fail, conf, mtbf, days_since_pm,
         reactive_count, risk_level, recommendation) = row

        new_prob = min(1.0, round(prob * prob_multiplier + random.uniform(-0.05, 0.05), 4))
        new_risk = degrade_risk(risk_level, risk_degradation_steps) if random.random() > 0.4 else risk_level
        new_days_to_fail = max(0, (days_to_fail or 0) + days_ago)

        backfilled.append((
            asset_id, target_date, new_prob, new_days_to_fail,
            round(conf * 0.95, 4), mtbf, days_since_pm, reactive_count,
            new_risk, recommendation, target_date
        ))

    cur.executemany("""
        INSERT INTO asset_failure_predictions
        (asset_id, prediction_date, failure_probability, days_to_predicted_failure,
         confidence_score, mtbf_days, days_since_last_pm, reactive_work_count_90d,
         risk_level, recommendation, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, backfilled)

    conn.commit()
    print(f"  {label} ({target_date}): inserted {len(backfilled)} predictions")


def main():
    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    print("\nBackfilling prediction dates for filter testing...")
    # 8 days ago — slightly better health (fewer criticals)
    backfill(conn, days_ago=8,  prob_multiplier=0.85, risk_degradation_steps=-1, label="8 days ago ")
    # 35 days ago — moderate health
    backfill(conn, days_ago=35, prob_multiplier=0.70, risk_degradation_steps=-1, label="35 days ago")
    # 95 days ago — healthier baseline
    backfill(conn, days_ago=95, prob_multiplier=0.50, risk_degradation_steps=-2, label="95 days ago")

    # Verify
    cur = conn.cursor()
    cur.execute("""
        SELECT prediction_date, COUNT(*) as cnt,
               SUM(CASE WHEN risk_level='CRITICAL' THEN 1 ELSE 0 END) as critical,
               SUM(CASE WHEN risk_level='HIGH' THEN 1 ELSE 0 END) as high
        FROM asset_failure_predictions
        GROUP BY prediction_date
        ORDER BY prediction_date DESC
    """)
    print("\nPredictions by date:")
    print(f"  {'Date':<14} {'Total':>6} {'Critical':>9} {'High':>6}")
    for row in cur.fetchall():
        print(f"  {row[0]:<14} {row[1]:>6} {row[2]:>9} {row[3]:>6}")

    conn.close()
    print("\nDone. Restart the backend API to pick up changes.")

if __name__ == "__main__":
    main()
