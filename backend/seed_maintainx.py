"""
Seed MaintainX with realistic test assets and work orders.

Run from repo root:
    python -m backend.seed_maintainx
"""

import json
import random
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .encryption import decrypt

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
BASE_URL = "https://api.getmaintainx.com/v1"

random.seed(42)

# (MaintainX display name, internal asset_id used in TrueSignal)
ASSETS = [
    ("Cooling Water Pump #1",   "PUMP-001"),
    ("Cooling Water Pump #2",   "PUMP-002"),
    ("Cooling Water Pump #3",   "PUMP-003"),
    ("Air Compressor #1",       "COMP-001"),
    ("Air Compressor #2",       "COMP-002"),
    ("Air Compressor #3",       "COMP-003"),
    ("Air Handling Unit #1",    "AHU-001"),
    ("Air Handling Unit #2",    "AHU-002"),
    ("Air Handling Unit #3",    "AHU-003"),
    ("Chilled Water System #1", "CHW-001"),
    ("Chilled Water System #2", "CHW-002"),
    ("Boiler #1",               "BOIL-001"),
]

TECHNICIANS = ["J. Martinez", "A. Patel", "D. Thompson", "R. Chen", "K. Williams"]
SITES = ["Plant A", "Plant B", "Plant C"]

# Work order templates: (title_template, type, priority, status, downtime_range, labor_range)
WO_TEMPLATES = [
    # Corrective — failures
    ("Pump seal failure — replacement required",      "REACTIVE", "HIGH",   "DONE", (4, 12), (3, 8)),
    ("Compressor overheating — emergency shutdown",   "REACTIVE", "HIGH",   "DONE", (6, 18), (4, 10)),
    ("Bearing noise — inspect and replace",           "REACTIVE", "MEDIUM", "DONE", (2, 6),  (2, 5)),
    ("Oil leak detected — seal inspection",           "REACTIVE", "MEDIUM", "DONE", (1, 4),  (1, 3)),
    ("Vibration alarm — balance check",               "REACTIVE", "MEDIUM", "DONE", (2, 8),  (2, 6)),
    ("Motor tripped — reset and inspect",             "REACTIVE", "HIGH",   "DONE", (1, 3),  (1, 2)),
    ("Belt wear — replacement",                       "REACTIVE", "LOW",    "DONE", (1, 2),  (1, 2)),
    ("Filter clogged — emergency replacement",        "REACTIVE", "MEDIUM", "DONE", (1, 3),  (1, 2)),
    ("Control valve failure — swap out",              "REACTIVE", "HIGH",   "DONE", (4, 10), (3, 6)),
    ("Coupling misalignment — realign",               "REACTIVE", "MEDIUM", "DONE", (2, 5),  (2, 4)),
    # Corrective — open/in-progress
    ("Intermittent pressure drop — diagnosis needed", "REACTIVE", "MEDIUM", "OPEN", (0, 0),  (0, 0)),
    ("Unusual noise on startup — inspect",            "REACTIVE", "LOW",    "OPEN", (0, 0),  (0, 0)),
    # Preventive — completed
    ("Monthly PM — lubrication and inspection",       "PREVENTIVE", "LOW",  "DONE", (0, 1),  (1, 2)),
    ("Quarterly PM — filter replacement",             "PREVENTIVE", "LOW",  "DONE", (0, 1),  (1, 3)),
    ("Annual PM — full overhaul",                     "PREVENTIVE", "MEDIUM","DONE",(2, 4),  (4, 8)),
    ("Belt and coupling inspection",                  "PREVENTIVE", "LOW",  "DONE", (0, 0),  (1, 2)),
    ("Electrical inspection and torque check",        "PREVENTIVE", "LOW",  "DONE", (0, 0),  (1, 2)),
    ("Vibration analysis — baseline reading",         "PREVENTIVE", "LOW",  "DONE", (0, 0),  (1, 1)),
    ("Oil sample and analysis",                       "PREVENTIVE", "LOW",  "DONE", (0, 0),  (0, 1)),
    # Preventive — open (upcoming)
    ("Monthly PM — due this week",                    "PREVENTIVE", "LOW",  "OPEN", (0, 0),  (0, 0)),
    ("Quarterly filter check — scheduled",            "PREVENTIVE", "LOW",  "OPEN", (0, 0),  (0, 0)),
]

# Assets that fail more often (weighted toward corrective WOs)
HIGH_FAILURE_ASSETS = {"PUMP-001", "COMP-001", "AHU-002"}


def get_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("No API key stored. Connect MaintainX in Settings first.")
    return decrypt(row[0], row[1], row[2])


def _request(method, path, api_key, payload, retries=3):
    url = f"{BASE_URL}/{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method=method
    )
    for attempt in range(retries):
        try:
            time.sleep(0.4)  # stay under rate limit
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ERROR {e.code}: {body}")
                return None
    return None


def api_post(path, api_key, payload):
    return _request("POST", path, api_key, payload)


def api_patch(path, api_key, payload):
    return _request("PATCH", path, api_key, payload)


def random_past_datetime(days_ago_min, days_ago_max):
    days_ago = random.randint(days_ago_min, days_ago_max)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def seed():
    api_key = get_key()

    # ── Create assets ──────────────────────────────────────────────────────────
    print(f"\nCreating {len(ASSETS)} assets...")
    mx_asset_ids = {}  # internal_id → maintainx_id

    for name, internal_id in ASSETS:
        result = api_post("assets", api_key, {
            "name": name,
            "description": f"TrueSignal test asset — {internal_id}",
            "serialNumber": internal_id,
        })
        if result and "id" in result:
            mx_asset_ids[internal_id] = result["id"]
            print(f"  ✓ {name} → MX id {result['id']}")
        else:
            print(f"  ✗ Failed to create {name}")

    # ── Create work orders ─────────────────────────────────────────────────────
    print(f"\nCreating work orders...")
    wo_count = 0

    for internal_id, mx_id in mx_asset_ids.items():
        is_high_failure = internal_id in HIGH_FAILURE_ASSETS
        # High-failure assets get more corrective WOs
        n_corrective = random.randint(5, 9) if is_high_failure else random.randint(2, 5)
        n_preventive = random.randint(3, 5)

        # Corrective (done)
        corrective_templates = [t for t in WO_TEMPLATES if t[1] == "REACTIVE" and t[3] == "DONE"]
        for _ in range(n_corrective):
            tmpl = random.choice(corrective_templates)
            title, wo_type, priority, status, downtime_r, labor_r = tmpl
            due_date = random_past_datetime(7, 180)
            completion_date = due_date

            payload = {
                "title": f"{title} — {internal_id}",
                "type": wo_type,
                "priority": priority,
                "assetId": mx_id,
                "dueDate": due_date,
                "description": f"Asset: {internal_id} | Site: {random.choice(SITES)} | Tech: {random.choice(TECHNICIANS)}",
            }
            result = api_post("workorders", api_key, payload)
            if result and "id" in result:
                # Patch to DONE with completedAt
                api_patch(f"workorders/{result['id']}", api_key, {
                    "status": "DONE",
                    "completedAt": f"{completion_date}T00:00:00.000Z",
                })
                wo_count += 1

        # Preventive (done)
        prev_templates = [t for t in WO_TEMPLATES if t[1] == "PREVENTIVE" and t[3] == "DONE"]
        for _ in range(n_preventive):
            tmpl = random.choice(prev_templates)
            title, wo_type, priority, status, downtime_r, labor_r = tmpl
            due_date = random_past_datetime(7, 180)

            payload = {
                "title": f"{title} — {internal_id}",
                "type": wo_type,
                "priority": priority,
                "assetId": mx_id,
                "dueDate": due_date,
                "description": f"Asset: {internal_id} | Site: {random.choice(SITES)} | Tech: {random.choice(TECHNICIANS)}",
            }
            result = api_post("workorders", api_key, payload)
            if result and "id" in result:
                api_patch(f"workorders/{result['id']}", api_key, {
                    "status": "DONE",
                    "completedAt": f"{due_date}T00:00:00.000Z",
                })
                wo_count += 1

        # Open WOs (a couple per asset)
        open_templates = [t for t in WO_TEMPLATES if t[3] == "OPEN"]
        for tmpl in random.sample(open_templates, k=min(2, len(open_templates))):
            title, wo_type, priority, status, _, _ = tmpl
            due_date = random_past_datetime(0, 14)
            payload = {
                "title": f"{title} — {internal_id}",
                "type": wo_type,
                "priority": priority,
                "assetId": mx_id,
                "dueDate": due_date,
                "description": f"Asset: {internal_id} | Site: {random.choice(SITES)}",
            }
            result = api_post("workorders", api_key, payload)
            if result and "id" in result:
                wo_count += 1

    print(f"\nDone. Created {len(mx_asset_ids)} assets and ~{wo_count} work orders in MaintainX.")
    print("Run the adapter next to pull this data into TrueSignal.")


if __name__ == "__main__":
    seed()
