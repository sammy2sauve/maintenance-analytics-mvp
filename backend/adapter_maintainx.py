"""
MaintainX adapter — fetches assets and work orders from MaintainX API
and upserts them into the TrueSignal work_orders table.

Run manually:
    python -m backend.adapter_maintainx

Called by the sync worker automatically on a schedule.
"""

import json
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from .encryption import decrypt

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
BASE_URL = "https://api.getmaintainx.com/v1"

# MaintainX -> internal field mappings
TYPE_MAP = {
    "REACTIVE":   "Corrective",
    "PREVENTIVE": "Preventive",
}
PRIORITY_MAP = {
    "HIGH":   "High",
    "MEDIUM": "Medium",
    "LOW":    "Low",
    "NONE":   "Low",
}
STATUS_MAP = {
    "OPEN":        "Open",
    "IN_PROGRESS": "Open",
    "ON_HOLD":     "Open",
    "DONE":        "Completed",
    "CANCELLED":   "Completed",
}
SITE_DEFAULT = "Plant A"
TECH_DEFAULT = "Unassigned"


# ── API helpers ────────────────────────────────────────────────────────────────

def _get(path, api_key, params="", retries=3):
    sep = "&" if "?" in path else "?"
    url = f"{BASE_URL}/{path}{sep}{params}" if params else f"{BASE_URL}/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    for attempt in range(retries):
        try:
            time.sleep(0.4)
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    return None


def fetch_all(resource_key, path, api_key):
    """Fetch all pages for a paginated endpoint."""
    results = []
    cursor = None
    while True:
        params = f"limit=100&cursor={cursor}" if cursor else "limit=100"
        data = _get(path, api_key, params)
        if not data:
            break
        results.extend(data.get(resource_key, []))
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return results


# ── Asset ID mapping ───────────────────────────────────────────────────────────

def build_asset_map(mx_assets):
    """
    Build a dict of MaintainX asset id -> internal asset_id.
    Assets seeded by TrueSignal have the internal ID in serialNumber.
    Falls back to a slug derived from the asset name.
    """
    mapping = {}
    for a in mx_assets:
        mx_id = a["id"]
        serial = a.get("serialNumber") or ""
        if serial and serial.isupper() and "-" in serial:
            # e.g. PUMP-001, AHU-002 — seeded by us
            mapping[mx_id] = serial
        else:
            # Derive from name: "Cooling Water Pump #1" -> "PUMP-001"
            mapping[mx_id] = _slug_from_name(a.get("name", f"ASSET-{mx_id}"))
    return mapping


def _slug_from_name(name: str) -> str:
    n = name.upper()
    if "PUMP" in n:      prefix = "PUMP"
    elif "COMPRESSOR" in n: prefix = "COMP"
    elif "AIR HAND" in n or "AHU" in n: prefix = "AHU"
    elif "CHILL" in n:   prefix = "CHW"
    elif "BOILER" in n:  prefix = "BOIL"
    elif "FAN" in n:     prefix = "FAN"
    elif "HVAC" in n:    prefix = "HVAC"
    elif "VFD" in n:     prefix = "VFD"
    elif "HEAT" in n or "HEX" in n: prefix = "HEX"
    else:                prefix = "ASSET"
    # Extract trailing number if present
    import re
    nums = re.findall(r"\d+", name)
    num = nums[-1].zfill(3) if nums else "001"
    return f"{prefix}-{num}"


# ── Work order mapping ─────────────────────────────────────────────────────────

def map_work_order(wo, asset_map):
    """Map a MaintainX work order to our internal work_orders schema."""
    mx_id = wo["id"]
    asset_id = asset_map.get(wo.get("assetId"))
    if not asset_id:
        return None  # skip work orders with unknown/deleted assets

    wo_type   = TYPE_MAP.get(wo.get("type", ""), "Corrective")
    priority  = PRIORITY_MAP.get(wo.get("priority", "NONE"), "Low")
    status    = STATUS_MAP.get(wo.get("status", "OPEN"), "Open")

    creation_date   = _parse_date(wo.get("createdAt"))
    due_date        = _parse_date(wo.get("dueDate"))
    completion_date = _parse_date(wo.get("completedAt"))

    # Treat past-due OPEN work orders as completed — MaintainX PATCH for
    # status/completedAt is not supported via API, so we infer completion
    # from dueDate being in the past.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not completion_date and due_date and due_date < today:
        status = "Completed"
        completion_date = due_date

    start_date = _parse_date(wo.get("startDate")) or creation_date

    # Estimate labor hours from estimatedTime (seconds)
    est_seconds = wo.get("estimatedTime") or 3600
    labor_scheduled = round(est_seconds / 3600, 1)
    labor_actual    = labor_scheduled if status == "Completed" else None

    # Reactive followup: corrective WOs that are marked high priority
    reactive_followup = 1 if (wo_type == "Corrective" and priority == "High") else 0

    return {
        "work_order_id":        mx_id,
        "asset_id":             asset_id,
        "site":                 SITE_DEFAULT,
        "type":                 wo_type,
        "status":               status,
        "technician":           TECH_DEFAULT,
        "creation_date":        creation_date,
        "scheduled_start":      due_date,
        "start_date":           start_date,
        "completion_date":      completion_date,
        "labor_hours_scheduled": labor_scheduled,
        "labor_hours_actual":   labor_actual,
        "downtime_hours":       None,
        "reactive_followup":    reactive_followup,
        "priority":             priority,
        "due_date":             due_date,
    }


def _parse_date(value):
    if not value:
        return None
    try:
        return value[:10]  # take YYYY-MM-DD from ISO string
    except Exception:
        return None


# ── DB upsert ──────────────────────────────────────────────────────────────────

def upsert_work_orders(rows):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            work_order_id        INTEGER PRIMARY KEY,
            asset_id             TEXT,
            site                 TEXT,
            type                 TEXT,
            status               TEXT,
            technician           TEXT,
            creation_date        DATE,
            scheduled_start      DATE,
            start_date           DATE,
            completion_date      DATE,
            labor_hours_scheduled REAL,
            labor_hours_actual   REAL,
            downtime_hours       REAL,
            reactive_followup    INTEGER,
            priority             TEXT,
            due_date             DATE
        )
    """)
    inserted = updated = 0
    for row in rows:
        existing = conn.execute(
            "SELECT work_order_id FROM work_orders WHERE work_order_id=?",
            (row["work_order_id"],)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE work_orders SET
                    asset_id=?, site=?, type=?, status=?, technician=?,
                    creation_date=?, scheduled_start=?, start_date=?,
                    completion_date=?, labor_hours_scheduled=?, labor_hours_actual=?,
                    downtime_hours=?, reactive_followup=?, priority=?, due_date=?
                WHERE work_order_id=?
            """, (
                row["asset_id"], row["site"], row["type"], row["status"], row["technician"],
                row["creation_date"], row["scheduled_start"], row["start_date"],
                row["completion_date"], row["labor_hours_scheduled"], row["labor_hours_actual"],
                row["downtime_hours"], row["reactive_followup"], row["priority"], row["due_date"],
                row["work_order_id"]
            ))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO work_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["work_order_id"], row["asset_id"], row["site"], row["type"],
                row["status"], row["technician"], row["creation_date"], row["scheduled_start"],
                row["start_date"], row["completion_date"], row["labor_hours_scheduled"],
                row["labor_hours_actual"], row["downtime_hours"], row["reactive_followup"],
                row["priority"], row["due_date"], 1
            ))
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, updated


# ── Main sync ──────────────────────────────────────────────────────────────────

def get_api_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("No MaintainX API key stored. Connect in Settings first.")
    return decrypt(row[0], row[1], row[2])


def mark_implemented_suggestions(location_id=1):
    """
    Flip pending PM suggestions to 'implemented' for any asset that has
    a completed work order in the last 30 days.
    Called after the pipeline so it operates on the freshest suggestions.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        UPDATE pm_optimization_suggestions
        SET status = 'implemented'
        WHERE status = 'pending'
          AND location_id = ?
          AND asset_id IN (
              SELECT DISTINCT asset_id FROM work_orders
              WHERE status = 'Completed'
                AND completion_date >= date('now', '-30 days')
                AND location_id = ?
          )
        """,
        (location_id, location_id),
    )
    marked = cursor.rowcount
    conn.commit()
    conn.close()
    return marked


def sync():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting MaintainX sync...")
    api_key = get_api_key()

    print("  Fetching assets...")
    mx_assets = fetch_all("assets", "assets", api_key)
    print(f"  -> {len(mx_assets)} assets found")

    asset_map = build_asset_map(mx_assets)

    print("  Fetching work orders...")
    mx_wos = fetch_all("workOrders", "workorders", api_key)
    print(f"  -> {len(mx_wos)} work orders found")

    mapped = [map_work_order(wo, asset_map) for wo in mx_wos if wo.get("assetId")]
    rows = [r for r in mapped if r is not None]
    skipped = len(mx_wos) - len(rows)
    if skipped:
        print(f"  -> {skipped} work orders skipped (no asset linked)")

    inserted, updated = upsert_work_orders(rows)
    print(f"  -> {inserted} inserted, {updated} updated in TrueSignal DB")
    print("Sync complete.")
    return inserted, updated


if __name__ == "__main__":
    sync()
