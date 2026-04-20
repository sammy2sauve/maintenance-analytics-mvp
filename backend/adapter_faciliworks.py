"""
FaciliWorks adapter — fetches assets, CMs, and PMs from the FaciliWorks Web API
and upserts them into the TrueSignal work_orders table.

Credentials are stored encrypted as "{base_url}|||{api_key}" in the existing
mx_api_key_enc/salt/nonce columns on the locations table (no migration needed).

Run manually:
    python -m backend.adapter_faciliworks

Called by the sync worker automatically on a schedule.

FaciliWorks API notes:
  - Auth: X-API-KEY header
  - Pagination: loadOptions JSON query param (DevExtreme style)
    e.g. /v1/assets?loadOptions={"skip":0,"take":100}
  - Dates: epoch time in seconds (not ISO strings)
  - Assets: GET /v1/assets -> {data: [...], totalCount: N}
  - CMs:    GET /v1/cm    -> {data: [...], totalCount: N}
  - PMs:    GET /v1/pm    -> {data: [...], totalCount: N}
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .encryption import decrypt
from .neon import get_conn

# ── Status / priority mappings ──────────────────────────────────────────────

# FaciliWorks status.comboBoxText → internal status
STATUS_MAP = {
    "open":        "Open",
    "in progress": "Open",
    "on hold":     "Open",
    "pending":     "Open",
    "complete":    "Completed",
    "completed":   "Completed",
    "closed":      "Completed",
    "cancelled":   "Completed",
    "canceled":    "Completed",
}

# FaciliWorks priority → internal priority
PRIORITY_MAP = {
    "high":     "High",
    "medium":   "Medium",
    "normal":   "Medium",
    "low":      "Low",
    "none":     "Low",
    "critical": "High",
}

PAGE_SIZE   = 100
SITE_DEFAULT = "Plant A"
TECH_DEFAULT = "Unassigned"
CRED_SEP    = "|||"  # delimiter for combined "base_url|||api_key" storage


# ── API helpers ──────────────────────────────────────────────────────────────

def _build_url(base_url: str, path: str, skip: int = 0, take: int = PAGE_SIZE) -> str:
    """Build a paginated FaciliWorks URL using loadOptions query param."""
    load_options = json.dumps({"skip": skip, "take": take})
    qs = urllib.parse.urlencode({"loadOptions": load_options})
    base = base_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}?{qs}"


def _get(url: str, api_key: str, retries: int = 3):
    req = urllib.request.Request(url, headers={"X-API-KEY": api_key})
    for attempt in range(retries):
        try:
            time.sleep(0.3)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 401:
                raise SystemExit("FaciliWorks: 401 Unauthorized. Check your API key.")
            else:
                body = e.read().decode(errors="replace")[:200]
                raise RuntimeError(f"FaciliWorks HTTP {e.code}: {body}")
    return None


def fetch_all_fw(path: str, api_key: str, base_url: str) -> list:
    """Paginate through all records for a FaciliWorks endpoint."""
    results = []
    skip = 0
    while True:
        url = _build_url(base_url, path, skip=skip, take=PAGE_SIZE)
        data = _get(url, api_key)
        if not data:
            break
        page = data.get("data", [])
        results.extend(page)
        total = data.get("totalCount", 0)
        skip += len(page)
        if skip >= total or not page:
            break
    return results


# ── Credential helpers ───────────────────────────────────────────────────────

def get_credentials(location_id=None) -> tuple[str, str]:
    """
    Returns (base_url, api_key) for the given location.
    Credentials stored as "{base_url}|||{api_key}" in mx_api_key_enc column.
    """
    conn = get_conn()
    cur = conn.cursor()
    if location_id is not None:
        cur.execute(
            "SELECT mx_api_key_enc, mx_api_key_salt, mx_api_key_nonce "
            "FROM locations WHERE id = %s",
            (location_id,),
        )
    else:
        cur.execute(
            "SELECT mx_api_key_enc, mx_api_key_salt, mx_api_key_nonce "
            "FROM locations WHERE mx_api_key_enc IS NOT NULL LIMIT 1"
        )
    row = cur.fetchone()
    conn.close()
    if not row or not row["mx_api_key_enc"]:
        raise SystemExit("No FaciliWorks credentials stored. Connect in Settings first.")
    raw = decrypt(row["mx_api_key_enc"], row["mx_api_key_salt"], row["mx_api_key_nonce"])
    if CRED_SEP in raw:
        base_url, api_key = raw.split(CRED_SEP, 1)
    else:
        raise SystemExit(
            "FaciliWorks credentials malformed. Expected 'base_url|||api_key' format."
        )
    return base_url.strip(), api_key.strip()


# ── Asset ID mapping ─────────────────────────────────────────────────────────

def build_asset_map(fw_assets: list) -> dict:
    """
    Map FaciliWorks EquipmentMasterID (int) -> internal asset_id (str).

    FaciliWorks EquipmentID is a user-defined string (often already the
    internal ID, e.g. "MMC-CHIL-001"). If it looks like our format
    (uppercase, hyphenated), use it directly; otherwise derive a slug.
    """
    mapping = {}
    for a in fw_assets:
        mid = a.get("equipmentMasterID") or a.get("EquipmentMasterID")
        eid = a.get("equipmentID") or a.get("EquipmentID") or ""
        name = a.get("description") or a.get("Description") or f"ASSET-{mid}"
        if eid and re.match(r"^[A-Z][A-Z0-9-]+$", eid):
            mapping[mid] = eid
        else:
            mapping[mid] = _slug_from_name(name)
    return mapping


def _slug_from_name(name: str) -> str:
    n = name.upper()
    if "PUMP" in n:                   prefix = "PUMP"
    elif "COMPRESSOR" in n:           prefix = "COMP"
    elif "AIR HAND" in n or "AHU" in n: prefix = "AHU"
    elif "CHILL" in n:                prefix = "CHW"
    elif "BOILER" in n:               prefix = "BOIL"
    elif "FAN" in n:                  prefix = "FAN"
    elif "HVAC" in n:                 prefix = "HVAC"
    elif "VFD" in n:                  prefix = "VFD"
    elif "HEAT" in n or "HEX" in n:  prefix = "HEX"
    elif "TOWER" in n:                prefix = "CTW"
    else:                             prefix = "ASSET"
    nums = re.findall(r"\d+", name)
    num = nums[-1].zfill(3) if nums else "001"
    return f"{prefix}-{num}"


# ── Date helpers ─────────────────────────────────────────────────────────────

def _epoch_to_date(epoch) -> str | None:
    """Convert FaciliWorks epoch-seconds timestamp to 'YYYY-MM-DD' string."""
    if not epoch:
        return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


# ── Work order mapping ────────────────────────────────────────────────────────

def _map_status(fw_status_text: str | None) -> str:
    if not fw_status_text:
        return "Open"
    return STATUS_MAP.get(fw_status_text.lower(), "Open")


def _map_priority(fw_priority: str | None) -> str:
    if not fw_priority:
        return "Low"
    return PRIORITY_MAP.get(fw_priority.lower(), "Low")


def map_work_order(wo: dict, asset_map: dict, wo_type: str) -> dict | None:
    """Map a FaciliWorks CM or PM record to our internal work_orders schema."""
    # Resolve asset
    asset_ref = wo.get("asset") or {}
    mid = asset_ref.get("equipmentMasterID") or asset_ref.get("EquipmentMasterID")
    asset_id = asset_map.get(mid)
    if not asset_id:
        # Try by EquipmentID only if it's already a known mapped value
        eid = asset_ref.get("equipmentID") or asset_ref.get("EquipmentID")
        if eid and eid in asset_map.values():
            asset_id = eid
    if not asset_id:
        return None

    # Work order identifier — prefer woNumber, fall back to maintenanceKey
    wo_id = str(wo.get("woNumber") or wo.get("maintenanceKey") or "")
    if not wo_id:
        return None

    # Status
    status_obj = wo.get("status") or {}
    status_text = status_obj.get("comboBoxText") if isinstance(status_obj, dict) else status_obj
    status = _map_status(status_text)

    # Priority
    pri_obj = wo.get("priority") or {}
    pri_text = pri_obj.get("comboBoxText") if isinstance(pri_obj, dict) else pri_obj
    priority = _map_priority(pri_text)

    # Dates (epoch seconds)
    creation_date   = _epoch_to_date(wo.get("createdDate") or wo.get("requestDate"))
    due_date        = _epoch_to_date(wo.get("dueDate"))
    completion_date = _epoch_to_date(wo.get("doneDate") or wo.get("completedDate"))

    # Infer completion from past dueDate for open WOs (same logic as MaintainX adapter)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not completion_date and due_date and due_date < today:
        status = "Completed"
        completion_date = due_date

    start_date = _epoch_to_date(wo.get("startDate")) or creation_date

    # Labor hours — FaciliWorks may have estimatedHours or actualHours
    labor_scheduled = float(wo.get("estimatedHours") or wo.get("estimatedLabor") or 1.0)
    labor_actual    = float(wo.get("actualHours") or wo.get("actualLabor") or 0) or (
        labor_scheduled if status == "Completed" else None
    )

    # Corrective + high priority → reactive followup flag
    reactive_followup = 1 if (wo_type == "Corrective" and priority == "High") else 0

    return {
        "work_order_id":          wo_id,
        "asset_id":               asset_id,
        "site":                   SITE_DEFAULT,
        "type":                   wo_type,
        "status":                 status,
        "technician":             TECH_DEFAULT,
        "creation_date":          creation_date,
        "scheduled_start":        due_date,
        "start_date":             start_date,
        "completion_date":        completion_date,
        "labor_hours_scheduled":  labor_scheduled,
        "labor_hours_actual":     labor_actual,
        "downtime_hours":         None,
        "reactive_followup":      reactive_followup,
        "priority":               priority,
        "due_date":               due_date,
    }


# ── DB upsert ─────────────────────────────────────────────────────────────────

def upsert_work_orders(rows: list, location_id: int = 1) -> tuple[int, int]:
    conn = get_conn()
    cur = conn.cursor()
    inserted = updated = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO work_orders (
                work_order_id, asset_id, site, type, status, technician,
                creation_date, scheduled_start, start_date, completion_date,
                labor_hours_scheduled, labor_hours_actual, downtime_hours,
                reactive_followup, priority, due_date, location_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (work_order_id) DO UPDATE SET
                asset_id              = EXCLUDED.asset_id,
                site                  = EXCLUDED.site,
                type                  = EXCLUDED.type,
                status                = EXCLUDED.status,
                technician            = EXCLUDED.technician,
                creation_date         = EXCLUDED.creation_date,
                scheduled_start       = EXCLUDED.scheduled_start,
                start_date            = EXCLUDED.start_date,
                completion_date       = EXCLUDED.completion_date,
                labor_hours_scheduled = EXCLUDED.labor_hours_scheduled,
                labor_hours_actual    = EXCLUDED.labor_hours_actual,
                downtime_hours        = EXCLUDED.downtime_hours,
                reactive_followup     = EXCLUDED.reactive_followup,
                priority              = EXCLUDED.priority,
                due_date              = EXCLUDED.due_date
            """,
            (
                row["work_order_id"], row["asset_id"], row["site"], row["type"],
                row["status"], row["technician"], row["creation_date"],
                row["scheduled_start"], row["start_date"], row["completion_date"],
                row["labor_hours_scheduled"], row["labor_hours_actual"],
                row["downtime_hours"], row["reactive_followup"],
                row["priority"], row["due_date"], location_id,
            ),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            updated += 1
    conn.commit()
    conn.close()
    return inserted, updated


# ── PM suggestion marking ─────────────────────────────────────────────────────

def mark_implemented_suggestions(location_id: int = 1) -> int:
    """
    Flip pending PM suggestions to 'implemented' for any asset that has
    a completed work order in the last 30 days.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE pm_optimization_suggestions
        SET status = 'implemented'
        WHERE status = 'pending'
          AND location_id = %s
          AND asset_id IN (
              SELECT DISTINCT asset_id FROM work_orders
              WHERE status = 'Completed'
                AND completion_date >= CURRENT_DATE - INTERVAL '30 days'
                AND location_id = %s
          )
        """,
        (location_id, location_id),
    )
    marked = cur.rowcount
    conn.commit()
    conn.close()
    return marked


# ── Main sync ─────────────────────────────────────────────────────────────────

def sync(location_id=None) -> tuple[int, int]:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting FaciliWorks sync...")
    base_url, api_key = get_credentials(location_id)

    print(f"  Base URL: {base_url}")

    # Fetch assets
    print("  Fetching assets...")
    fw_assets = fetch_all_fw("v1/assets", api_key, base_url)
    print(f"  -> {len(fw_assets)} assets found")
    asset_map = build_asset_map(fw_assets)

    # Fetch corrective maintenance (CMs)
    print("  Fetching corrective maintenance (CM)...")
    cms = fetch_all_fw("v1/cm", api_key, base_url)
    print(f"  -> {len(cms)} CM records found")

    # Fetch preventive maintenance (PMs)
    print("  Fetching preventive maintenance (PM)...")
    pms = fetch_all_fw("v1/pm", api_key, base_url)
    print(f"  -> {len(pms)} PM records found")

    # Map to internal schema
    rows = []
    skipped = 0
    for wo in cms:
        mapped = map_work_order(wo, asset_map, "Corrective")
        if mapped:
            rows.append(mapped)
        else:
            skipped += 1
    for wo in pms:
        mapped = map_work_order(wo, asset_map, "Preventive")
        if mapped:
            rows.append(mapped)
        else:
            skipped += 1

    if skipped:
        print(f"  -> {skipped} records skipped (no linked asset or missing ID)")

    # Deduplicate by work_order_id (last write wins — shouldn't happen but safe)
    deduped = {r["work_order_id"]: r for r in rows}
    rows = list(deduped.values())

    inserted, updated = upsert_work_orders(rows, location_id or 1)
    print(f"  -> {inserted} inserted, {updated} updated in TrueSignal DB")
    print("Sync complete.")
    return inserted, updated


# ── Push work order to FaciliWorks ────────────────────────────────────────────

def push_pm_as_work_order(suggestion: dict, base_url: str, api_key: str) -> str:
    """
    Push a PM suggestion as a new Corrective Maintenance work order to FaciliWorks.
    Returns the created WO identifier (woNumber or maintenanceKey as string).
    """
    # Reverse map: internal asset_id -> FW equipmentMasterID
    fw_assets = fetch_all_fw("v1/assets", api_key, base_url)
    asset_map = build_asset_map(fw_assets)
    reverse_map = {v: k for k, v in asset_map.items()}

    asset_id = suggestion["asset_id"]
    mid = reverse_map.get(asset_id)
    if not mid:
        raise ValueError(f"Asset '{asset_id}' not found in FaciliWorks. Run a sync first.")

    due_epoch = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())

    description = (
        f"PM Frequency Optimization — Adjust from "
        f"{suggestion['current_pm_frequency_days']}d to "
        f"{suggestion['suggested_pm_frequency_days']}d interval.\n"
        f"Reason: {suggestion.get('reason', '')}"
    )

    payload = json.dumps({
        "asset": {"equipmentMasterID": mid},
        "description": description,
        "priority": {"comboBoxText": "Medium"},
        "dueDate": due_epoch,
        "estimatedHours": 2.0,
        "requestedBy": "TrueSignal Predictive Intelligence",
    }).encode()

    url = f"{base_url.rstrip('/')}/v1/cm"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())

    return str(result.get("woNumber") or result.get("maintenanceKey") or result.get("id") or "")


if __name__ == "__main__":
    sync()
