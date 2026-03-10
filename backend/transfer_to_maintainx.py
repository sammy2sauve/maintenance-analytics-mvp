"""
Transfer all synthetic work orders into MaintainX.

1. Fetches existing MaintainX assets (by serialNumber) to avoid duplicates
2. Creates any missing assets
3. Creates all 618 synthetic work orders

Run from repo root:
    python -m backend.transfer_to_maintainx

Takes ~8-10 minutes due to MaintainX rate limiting.
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

TYPE_MAP   = {"Corrective": "REACTIVE", "Preventive": "PREVENTIVE"}
PRIORITY_MAP = {"High": "HIGH", "Medium": "MEDIUM", "Low": "LOW"}

ASSET_LABELS = {
    "PUMP": "Pump", "COMP": "Air Compressor", "AHU": "Air Handling Unit",
    "HEX": "Heat Exchanger", "VFD": "VFD Drive", "HVAC": "HVAC Unit",
    "CHW": "Chilled Water System", "CW": "Cooling Water Pump",
    "FAN": "Supply Fan", "RTU": "Rooftop Unit", "BOIL": "Boiler",
    "CTW": "Cooling Tower", "EXH": "Exhaust Fan",
}


def asset_display_name(internal_id: str) -> str:
    prefix = internal_id.split("-")[0]
    label = ASSET_LABELS.get(prefix, prefix)
    return f"{label} {internal_id}"


# ── API helpers ────────────────────────────────────────────────────────────────

def get_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("No API key stored. Connect MaintainX in Settings first.")
    return decrypt(row[0], row[1], row[2])


def _request(method, path, api_key, payload=None, retries=4):
    url = f"{BASE_URL}/{path}"
    data = json.dumps(payload).encode() if payload else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(retries):
        try:
            time.sleep(0.5)
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ERROR {e.code}: {body[:120]}")
                return None
    return None


def fetch_all_assets(api_key):
    results, cursor = [], None
    while True:
        params = f"limit=100&cursor={cursor}" if cursor else "limit=100"
        data = _request("GET", f"assets?{params}", api_key)
        if not data:
            break
        results.extend(data.get("assets", []))
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return results


# ── Load synthetic data ────────────────────────────────────────────────────────

def load_synthetic_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    assets = [
        dict(r) for r in conn.execute(
            "SELECT DISTINCT asset_id FROM work_orders WHERE work_order_id < 1000000"
        ).fetchall()
    ]
    wos = [
        dict(r) for r in conn.execute(
            "SELECT * FROM work_orders WHERE work_order_id < 1000000"
        ).fetchall()
    ]
    conn.close()
    return [a["asset_id"] for a in assets], wos


# ── Main transfer ──────────────────────────────────────────────────────────────

def transfer():
    api_key = get_key()

    print("Fetching existing MaintainX assets...")
    existing = fetch_all_assets(api_key)
    # Map serialNumber -> MX asset id for assets we already created
    serial_to_mx = {
        a["serialNumber"]: a["id"]
        for a in existing
        if a.get("serialNumber")
    }
    print(f"  {len(existing)} assets in MaintainX, {len(serial_to_mx)} with serial numbers")

    synthetic_asset_ids, wos = load_synthetic_data()
    print(f"\nSynthetic data: {len(synthetic_asset_ids)} unique assets, {len(wos)} work orders")

    # ── Step 1: create missing assets ─────────────────────────────────────────
    missing = [aid for aid in synthetic_asset_ids if aid not in serial_to_mx]
    print(f"\nCreating {len(missing)} missing assets in MaintainX...")
    created_assets = 0
    for aid in missing:
        result = _request("POST", "assets", api_key, {
            "name": asset_display_name(aid),
            "serialNumber": aid,
            "description": f"TrueSignal asset — {aid}",
        })
        if result and "id" in result:
            serial_to_mx[aid] = result["id"]
            created_assets += 1
            if created_assets % 20 == 0:
                print(f"  {created_assets}/{len(missing)} assets created...")
        else:
            print(f"  Failed to create {aid}")

    print(f"  Done — {created_assets} assets created")

    # ── Step 2: create work orders ─────────────────────────────────────────────
    print(f"\nCreating {len(wos)} work orders in MaintainX...")
    created_wos = skipped = 0

    for i, wo in enumerate(wos):
        asset_id = wo["asset_id"]
        mx_asset_id = serial_to_mx.get(asset_id)
        if not mx_asset_id:
            skipped += 1
            continue

        mx_type = TYPE_MAP.get(wo.get("type", "Corrective"), "REACTIVE")
        mx_priority = PRIORITY_MAP.get(wo.get("priority", "Low"), "LOW")

        due = wo.get("due_date") or wo.get("creation_date")
        due_dt = f"{due}T08:00:00.000Z" if due else None

        payload = {
            "title": f"{wo.get('type', 'Work Order')} — {asset_id}",
            "type": mx_type,
            "priority": mx_priority,
            "assetId": mx_asset_id,
            "description": (
                f"Asset: {asset_id} | Site: {wo.get('site', '')} | "
                f"Tech: {wo.get('technician', '')} | "
                f"Status: {wo.get('status', '')}"
            ),
        }
        if due_dt:
            payload["dueDate"] = due_dt

        result = _request("POST", "workorders", api_key, payload)
        if result and "id" in result:
            created_wos += 1
        else:
            skipped += 1

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(wos)} processed ({created_wos} created, {skipped} skipped)...")

    print(f"\nTransfer complete.")
    print(f"  Assets created: {created_assets}")
    print(f"  Work orders created: {created_wos}")
    print(f"  Skipped: {skipped}")
    print("\nNext: run the sync + pipeline to update the dashboard.")


if __name__ == "__main__":
    transfer()
