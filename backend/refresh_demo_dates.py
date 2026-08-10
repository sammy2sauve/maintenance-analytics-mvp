"""
refresh_demo_dates.py — Roll all demo data dates forward so the app always shows fresh data.

Finds the gap between today and the most recent work order for location_id=3,
then shifts every date column in every demo table forward by that many days.
The latest work order always ends up dated today, regardless of when the script last ran.

Tables updated (location_id=3 only):
  - work_orders         : creation_date, scheduled_start, start_date, completion_date, due_date
  - asset_failure_predictions : prediction_date
  - pm_optimization_suggestions : suggestion_date
  - maintenance_insights : insight_date

Run weekly via GitHub Actions (see .github/workflows/refresh-demo-dates.yml).
Usage: python -m backend.refresh_demo_dates
"""

import os
from datetime import date
from .neon import get_db

DEMO_LOCATION_ID = int(os.environ.get("DEMO_LOCATION_ID", "3"))


def refresh_demo_dates() -> dict:
    with get_db() as conn:
        cur = conn.cursor()

        # Determine the shift: today minus the latest date in the demo work orders
        cur.execute("""
            SELECT MAX(GREATEST(
                COALESCE(creation_date,   '2000-01-01'::date),
                COALESCE(completion_date, '2000-01-01'::date),
                COALESCE(due_date,        '2000-01-01'::date)
            )) AS max_date
            FROM work_orders
            WHERE location_id = %s
        """, (DEMO_LOCATION_ID,))
        row = cur.fetchone()
        max_date = row['max_date'] if row else None

        if not max_date:
            return {"status": "skipped", "reason": "no work orders found for demo location"}

        today = date.today()
        shift_days = (today - max_date).days

        if shift_days <= 0:
            return {"status": "skipped", "reason": f"data already current (max date: {max_date})"}

        results = {"status": "ok", "shift_days": shift_days, "max_was": str(max_date), "today": str(today)}

        # work_orders — 5 date columns, all nullable
        cur.execute("""
            UPDATE work_orders SET
                creation_date   = CASE WHEN creation_date   IS NOT NULL THEN creation_date   + make_interval(days => %s) END,
                scheduled_start = CASE WHEN scheduled_start IS NOT NULL THEN scheduled_start + make_interval(days => %s) END,
                start_date      = CASE WHEN start_date      IS NOT NULL THEN start_date      + make_interval(days => %s) END,
                completion_date = CASE WHEN completion_date IS NOT NULL THEN completion_date + make_interval(days => %s) END,
                due_date        = CASE WHEN due_date        IS NOT NULL THEN due_date        + make_interval(days => %s) END
            WHERE location_id = %s
        """, (shift_days, shift_days, shift_days, shift_days, shift_days, DEMO_LOCATION_ID))
        results["work_orders"] = cur.rowcount

        # asset_failure_predictions
        cur.execute("""
            UPDATE asset_failure_predictions
            SET prediction_date = prediction_date + make_interval(days => %s)
            WHERE location_id = %s
        """, (shift_days, DEMO_LOCATION_ID))
        results["asset_failure_predictions"] = cur.rowcount

        # pm_optimization_suggestions
        cur.execute("""
            UPDATE pm_optimization_suggestions
            SET suggestion_date = suggestion_date + make_interval(days => %s)
            WHERE location_id = %s
        """, (shift_days, DEMO_LOCATION_ID))
        results["pm_optimization_suggestions"] = cur.rowcount

        # maintenance_insights
        cur.execute("""
            UPDATE maintenance_insights
            SET insight_date = insight_date + make_interval(days => %s)
            WHERE location_id = %s
        """, (shift_days, DEMO_LOCATION_ID))
        results["maintenance_insights"] = cur.rowcount

        return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = refresh_demo_dates()
    print(result)
