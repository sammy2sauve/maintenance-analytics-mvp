"""
Migrate operational data from local SQLite to Neon PostgreSQL.

Auth data (orgs/locations/users) already exists in Neon — skip those.
Work orders and predictions used location_id=1 (old hardcoded value);
we remap them to location_id=3 (the real Thunderco location in Neon).

Usage:
    python -m backend.migrate_to_neon
"""

import sqlite3
from pathlib import Path

from .neon import get_conn

SQLITE_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"

# Old location_id in SQLite data → real location_id in Neon
LOCATION_REMAP = {1: 3}


def _sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def remap_loc(loc_id):
    """Map stale location_id to the correct Neon location_id."""
    if loc_id is None:
        return 3  # default to the only location
    return LOCATION_REMAP.get(loc_id, loc_id)


def migrate_work_orders(pg, sq):
    cur_sq = sq.cursor()
    try:
        cur_sq.execute("SELECT * FROM work_orders")
    except Exception:
        print("  work_orders: table not found (skipped)")
        return
    rows = cur_sq.fetchall()
    if not rows:
        print("  work_orders: 0 rows (skipped)")
        return
    cur_pg = pg.cursor()
    n = 0
    for r in rows:
        keys = r.keys()
        location_id = remap_loc(r['location_id'] if 'location_id' in keys else None)
        cur_pg.execute("""
            INSERT INTO work_orders (
                work_order_id, asset_id, site, type, status, technician,
                creation_date, scheduled_start, start_date, completion_date,
                labor_hours_scheduled, labor_hours_actual, downtime_hours,
                reactive_followup, priority, due_date, location_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (work_order_id) DO NOTHING
        """, (
            r['work_order_id'], r['asset_id'], r['site'], r['type'],
            r['status'], r['technician'], r['creation_date'], r['scheduled_start'],
            r['start_date'], r['completion_date'], r['labor_hours_scheduled'],
            r['labor_hours_actual'], r['downtime_hours'], r['reactive_followup'],
            r['priority'], r['due_date'], location_id,
        ))
        n += cur_pg.rowcount
    pg.commit()
    print(f"  work_orders: {n} inserted")


def migrate_kpis(pg, sq, table, period_col):
    cur_sq = sq.cursor()
    try:
        cur_sq.execute(f"SELECT * FROM {table}")
    except Exception:
        print(f"  {table}: table not found (skipped)")
        return
    rows = cur_sq.fetchall()
    if not rows:
        print(f"  {table}: 0 rows (skipped)")
        return
    cur_pg = pg.cursor()
    n = 0
    for r in rows:
        cur_pg.execute(f"""
            INSERT INTO {table} ({period_col}, kpi_name, raw_value, truesignal_value, distortion_flag, explanation_text)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT ({period_col}, kpi_name) DO NOTHING
        """, (
            r[period_col], r['kpi_name'], r['raw_value'], r['truesignal_value'],
            bool(r['distortion_flag']), r['explanation_text'],
        ))
        n += cur_pg.rowcount
    pg.commit()
    print(f"  {table}: {n} inserted")


def migrate_predictions(pg, sq):
    cur_sq = sq.cursor()
    try:
        cur_sq.execute("SELECT * FROM asset_failure_predictions")
    except Exception:
        print("  asset_failure_predictions: table not found (skipped)")
        return
    rows = cur_sq.fetchall()
    if not rows:
        print("  asset_failure_predictions: 0 rows (skipped)")
        return
    cur_pg = pg.cursor()
    n = 0
    for r in rows:
        keys = r.keys()
        location_id = remap_loc(r['location_id'] if 'location_id' in keys else None)
        cur_pg.execute("""
            INSERT INTO asset_failure_predictions (
                asset_id, prediction_date, failure_probability, days_to_predicted_failure,
                confidence_score, mtbf_days, days_since_last_pm, reactive_work_count_90d,
                risk_level, recommendation, location_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset_id, prediction_date, location_id) DO NOTHING
        """, (
            r['asset_id'], r['prediction_date'], r['failure_probability'],
            r['days_to_predicted_failure'], r['confidence_score'], r['mtbf_days'],
            r['days_since_last_pm'], r['reactive_work_count_90d'],
            r['risk_level'], r['recommendation'], location_id,
        ))
        n += cur_pg.rowcount
    pg.commit()
    print(f"  asset_failure_predictions: {n} inserted")


def migrate_pm_suggestions(pg, sq):
    cur_sq = sq.cursor()
    try:
        cur_sq.execute("SELECT * FROM pm_optimization_suggestions")
    except Exception:
        print("  pm_optimization_suggestions: table not found (skipped)")
        return
    rows = cur_sq.fetchall()
    if not rows:
        print("  pm_optimization_suggestions: 0 rows (skipped)")
        return
    cur_pg = pg.cursor()
    n = 0
    # Deduplicate on (asset_id, location_id) keeping latest suggestion_date
    seen = set()
    rows_sorted = sorted(rows, key=lambda r: r['suggestion_date'] or '', reverse=True)
    for r in rows_sorted:
        keys = r.keys()
        location_id = remap_loc(r['location_id'] if 'location_id' in keys else None)
        key = (r['asset_id'], location_id)
        if key in seen:
            continue
        seen.add(key)
        cur_pg.execute("""
            INSERT INTO pm_optimization_suggestions (
                asset_id, current_pm_frequency_days, suggested_pm_frequency_days,
                reason, estimated_cost_savings, estimated_risk_change,
                confidence_score, reactive_work_after_pm_count,
                suggestion_date, status, location_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset_id, location_id) DO NOTHING
        """, (
            r['asset_id'], r['current_pm_frequency_days'], r['suggested_pm_frequency_days'],
            r['reason'], r['estimated_cost_savings'], r['estimated_risk_change'],
            r['confidence_score'], r['reactive_work_after_pm_count'],
            r['suggestion_date'], r['status'], location_id,
        ))
        n += cur_pg.rowcount
    pg.commit()
    print(f"  pm_optimization_suggestions: {n} inserted")


def migrate_insights(pg, sq):
    cur_sq = sq.cursor()
    try:
        cur_sq.execute("SELECT * FROM maintenance_insights")
    except Exception:
        print("  maintenance_insights: table not found (skipped)")
        return
    rows = cur_sq.fetchall()
    if not rows:
        print("  maintenance_insights: 0 rows (skipped)")
        return
    cur_pg = pg.cursor()
    n = 0
    for r in rows:
        keys = r.keys()
        location_id = remap_loc(r['location_id'] if 'location_id' in keys else None)
        cur_pg.execute("""
            INSERT INTO maintenance_insights (
                insight_type, title, description, confidence_score,
                impact_level, affected_assets, metric_value, insight_date, location_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (insight_type, title, location_id) DO NOTHING
        """, (
            r['insight_type'], r['title'], r['description'], r['confidence_score'],
            r['impact_level'], r['affected_assets'], r['metric_value'],
            r['insight_date'], location_id,
        ))
        n += cur_pg.rowcount
    pg.commit()
    print(f"  maintenance_insights: {n} inserted")


def migrate():
    if not SQLITE_PATH.exists():
        print(f"SQLite DB not found at {SQLITE_PATH} -- nothing to migrate.")
        return

    print(f"Migrating operational data from SQLite to Neon...")
    print("  (Auth data skipped -- already in Neon)")
    sq = _sqlite()
    pg = get_conn()

    try:
        migrate_work_orders(pg, sq)
        migrate_kpis(pg, sq, 'daily_kpis', 'period_date')
        migrate_kpis(pg, sq, 'weekly_kpis', 'period_week')
        migrate_kpis(pg, sq, 'monthly_kpis', 'period_month')
        migrate_predictions(pg, sq)
        migrate_pm_suggestions(pg, sq)
        migrate_insights(pg, sq)
        print("\nMigration complete.")
    except Exception as e:
        pg.rollback()
        print(f"\nMigration FAILED: {e}")
        raise
    finally:
        sq.close()
        pg.close()


if __name__ == "__main__":
    migrate()
